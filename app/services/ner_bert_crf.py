"""Implementasi NER dengan model BERT + BiLSTM + CRF milik tim.

Model yang dipakai adalah checkpoint BERT-CRF (fine-tuned untuk NER bahasa
Indonesia). Arsitekturnya: BERT -> BiLSTM -> Linear(11 label) -> CRF.

Karena checkpoint ini bukan `BertForTokenClassification` standar HuggingFace,
`pipeline("token-classification")` tidak bisa memakainya. Modul ini
mengimplementasikan sendiri pemuatan bobot, lapisan BiLSTM, klasifikasi
per-token, dan decoding Viterbi untuk lapisan CRF.

Peta label model ke empat kategori pada proposal:

    DATE -> Date      DIS -> Disaster
    LOC  -> Location  PER -> Person

Label ORG (organisasi) sengaja diabaikan karena proposal hanya mengenali
empat kategori entitas.
"""

import json
from pathlib import Path

# Label model (BIO) -> kategori entitas pada proposal.
LABEL_TO_ENTITY_TYPE = {
    "DATE": "Date",
    "DIS": "Disaster",
    "LOC": "Location",
    "PER": "Person",
}


class BertCrfNer:
    """Mesin NER berbasis checkpoint BERT-CRF di folder lokal.

    Bobot dimuat manual: `config.json` tidak disertakan pada checkpoint, jadi
    arsitektur BERT dibangun dari ukuran tensor pada state dict. Dengan begitu
    folder model cukup berisi `best_model.pt`, `tokenizer.json`, dan
    `tokenizer_config.json`.
    """

    def __init__(self, model_path: str):
        try:
            import torch
            from torch import nn
            from transformers import AutoTokenizer, BertConfig, BertModel
        except ImportError as exc:
            raise RuntimeError(
                "Install torch dan transformers untuk NER backend transformers"
            ) from exc

        self._torch = torch
        self._model_path = Path(model_path)
        if not self._model_path.is_dir():
            raise ValueError(f"Folder model NER tidak ditemukan: {model_path}")

        self._labels = self._load_labels()
        self._tokenizer = AutoTokenizer.from_pretrained(str(self._model_path))
        self._model = self._build_model(BertConfig, BertModel, torch, nn)

    # ------------------------------------------------------------------ #
    # Pemuatan
    # ------------------------------------------------------------------ #

    def _load_labels(self) -> list[str]:
        """Baca label2id.json lalu balik jadi daftar label per id."""
        label_file = self._model_path / "label2id.json"
        if not label_file.exists():
            raise ValueError(f"label2id.json tidak ditemukan di {self._model_path}")
        label2id = json.loads(label_file.read_text(encoding="utf-8"))
        # id2label: indeks id -> nama label, supaya urutan kelas CRF pasti.
        labels = [None] * (max(label2id.values()) + 1)
        for name, index in label2id.items():
            labels[index] = name
        return labels

    def _build_model(self, BertConfig, BertModel, torch, nn):
        """Bangun arsitektur dari state dict lalu muat bobot hasil training."""
        state_dict = torch.load(
            self._model_path / "best_model.pt", map_location="cpu", weights_only=False
        )
        if hasattr(state_dict, "state_dict"):
            state_dict = state_dict.state_dict()

        word_embeddings = state_dict["bert.embeddings.word_embeddings.weight"]
        position_embeddings = state_dict["bert.embeddings.position_embeddings.weight"]
        lstm_weight = state_dict["lstm.weight_ih_l0"]
        classifier_weight = state_dict["classifier.weight"]

        # BiLSTM: weight_ih_l0 punya bentuk (4 * hidden, input_size).
        # Karena itu hidden_size diambil dari ukuran barisnya dibagi empat.
        lstm_hidden_size = lstm_weight.shape[0] // 4

        num_layers = 1 + max(
            int(k.split(".")[3])
            for k in state_dict
            if k.startswith("bert.encoder.layer.")
        )
        config = BertConfig(
            vocab_size=word_embeddings.shape[0],
            hidden_size=word_embeddings.shape[1],
            num_hidden_layers=num_layers,
            num_attention_heads=12,
            intermediate_size=state_dict[
                "bert.encoder.layer.0.intermediate.dense.weight"
            ].shape[0],
            max_position_embeddings=position_embeddings.shape[0],
            type_vocab_size=state_dict[
                "bert.embeddings.token_type_embeddings.weight"
            ].shape[0],
        )

        self._lstm_hidden_size = lstm_hidden_size
        self._num_labels = classifier_weight.shape[0]

        bert = BertModel(config)
        # Checkpoint memakai prefiks "bert." karena berasal dari wrapper model
        # (bert + lstm + classifier). `BertModel` sendiri menyimpan kunci
        # tanpa prefiks, jadi ia harus dilepas dulu — kalau tidak, load
        # `strict=False` diam-diam menolak seluruh bobot dan menghasilkan
        # model acak yang tidak mendeteksi apa pun.
        bert_state = {
            k[len("bert.") :]: v
            for k, v in state_dict.items()
            if k.startswith("bert.")
        }
        missing, unexpected = bert.load_state_dict(bert_state, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                "Bobot BERT tidak cocok dengan model tersimpan. "
                f"missing={len(missing)} unexpected={len(unexpected)}; "
                f"contoh missing={missing[:3]}; contoh unexpected={unexpected[:3]}"
            )

        lstm = nn.LSTM(
            input_size=config.hidden_size,
            hidden_size=self._lstm_hidden_size,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        lstm_state = {
            k[len("lstm.") :]: v for k, v in state_dict.items() if k.startswith("lstm.")
        }
        lstm.load_state_dict(lstm_state)

        classifier = nn.Linear(self._lstm_hidden_size * 2, self._num_labels)
        classifier.load_state_dict(
            {
                "weight": state_dict["classifier.weight"],
                "bias": state_dict["classifier.bias"],
            }
        )

        crf = ConditionalRandomField(self._num_labels)
        crf.load_state_dict(
            {
                "start_transitions": state_dict["crf.start_transitions"],
                "end_transitions": state_dict["crf.end_transitions"],
                "transitions": state_dict["crf.transitions"],
            }
        )

        class _BertCrfModel(nn.Module):
            def __init__(self, encoder, lstm, classifier, crf):
                super().__init__()
                self.encoder = encoder
                self.lstm = lstm
                self.classifier = classifier
                self.crf = crf

            def forward(self, input_ids, attention_mask, token_type_ids=None):
                outputs = self.encoder(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    token_type_ids=token_type_ids,
                )
                sequence = self.lstm(outputs.last_hidden_state)[0]
                return self.classifier(sequence)

        model = _BertCrfModel(bert, lstm, classifier, crf)
        model.eval()
        return model

    # ------------------------------------------------------------------ #
    # Inferensi
    # ------------------------------------------------------------------ #

    def extract(self, text: str) -> list:
        """Ekstrak entitas dari teks.

        Mengembalikan daftar `ExtractedEntity` dengan posisi karakter pada
        teks asli (dihitung lewat offset mapping tokenizer).
        """
        from app.services.ner import ExtractedEntity

        torch = self._torch
        if not text or not text.strip():
            return []

        encoding = self._tokenizer(
            text,
            return_tensors="pt",
            return_offsets_mapping=True,
            truncation=True,
            max_length=512,
        )
        offsets = self._normalize_offsets(encoding.pop("offset_mapping"))
        model_inputs = {
            key: value
            for key, value in encoding.items()
            if key in self._tokenizer.model_input_names
        }

        with torch.no_grad():
            logits = self._model(**model_inputs)[0]

        tag_ids = self._model.crf.decode(logits, self._mask(offsets))

        results = []
        # Akumulator entitas yang sedang terbuka: label model memakai BIO,
        # jadi beberapa token (sub-word) boleh menyatu jadi satu entitas.
        current_type: str | None = None
        current_start = current_end = 0

        def flush():
            if current_type is None or current_end <= current_start:
                return None
            return ExtractedEntity(
                jenis_entitas=current_type,
                nilai_teks=text[current_start:current_end].strip(),
                char_start=current_start,
                char_end=current_end,
            )

        for label_id, (start, end) in zip(tag_ids, offsets):
            label = self._labels[label_id]

            # Token tanpa entitas, token khusus ([CLS]/[SEP]), atau token
            # sub-word tanpa karakter asli: tutup entitas yang sedang terbuka.
            if not label or label == "O" or end <= start:
                finished = flush()
                if finished:
                    results.append(finished)
                current_type = None
                continue

            # Buang prefiks BIO ("B-DIS" -> "DIS") sebelum cocok ke proposal.
            base_label = label[2:] if label.startswith(("B-", "I-")) else label
            entity_type = LABEL_TO_ENTITY_TYPE.get(base_label)

            # Label di luar proposal (mis. ORG) sengaja dilewati.
            if entity_type is None:
                finished = flush()
                if finished:
                    results.append(finished)
                current_type = None
                continue

            starts_new = entity_type != current_type or label.startswith("B-")
            if starts_new:
                finished = flush()
                if finished:
                    results.append(finished)
                current_type = entity_type
                current_start, current_end = start, end
            else:
                # Lanjutan (I-*) atau sub-word berikutnya: satukan teksnya.
                current_end = end

        finished = flush()
        if finished:
            results.append(finished)
        return results

    def _normalize_offsets(self, raw) -> list[tuple[int, int]]:
        """Samakan bentuk offset mapping jadi daftar pasangan (start, end).

        Transformers 5.x mengembalikan daftar bertingkat, sedangkan versi lama
        mengembalikan tensor (batch, token, 2). Dua bentuk ini dinormalkan di
        sini supaya pemanggilan model tidak bergantung versi pustaka.
        """
        if hasattr(raw, "tolist"):
            raw = raw.tolist()
        # Bentuk [[(s, e), ...]] -> ambil baris pertama.
        if raw and isinstance(raw[0], list) and raw[0] and isinstance(raw[0][0], list):
            raw = raw[0]
        return [(int(start), int(end)) for start, end in raw]

    def _mask(self, offsets):
        """Buat mask dari offset mapping (token tanpa teks diabaikan).

        Dikembalikan sebagai tensor boolean supaya operasi negasi (`~`)
        berarti "bukan" -- pada tensor integer, `~` berarti bitwise NOT.
        """
        torch = self._torch
        mask = [end > start for start, end in offsets]
        return torch.tensor(mask, dtype=torch.bool)


class ConditionalRandomField:
    """Lapisan CRF linear dengan decoding Viterbi.

    Menggantikan paket `pytorch-crf` supaya dependensi produksi tetap ringan
    dan tidak perlu pustaka tambahan yang tidak terkurasi.
    """

    def __init__(self, num_tags: int):
        import torch
        from torch import nn

        self._torch = torch
        self.start_transitions = nn.Parameter(torch.zeros(num_tags))
        self.end_transitions = nn.Parameter(torch.zeros(num_tags))
        self.transitions = nn.Parameter(torch.zeros(num_tags, num_tags))

    def load_state_dict(self, state_dict: dict, strict: bool = True) -> None:
        with self._torch.no_grad():
            self.start_transitions.copy_(state_dict["start_transitions"])
            self.end_transitions.copy_(state_dict["end_transitions"])
            self.transitions.copy_(state_dict["transitions"])

    def decode(self, logits, mask=None) -> list[int]:
        """Viterbi: skor terbaik per label untuk setiap token.

        `logits` harus berbentuk (token, label) dua dimensi. `mask` berbentuk
        (token,) dengan nilai 1 untuk token yang punya teks dan 0 untuk token
        khusus seperti [CLS]/[SEP] dan sub-word tanpa karakter asli.

        Mengembalikan daftar id label untuk setiap posisi token.
        """
        torch = self._torch

        # Normalkan bentuk logits menjadi (token, label).
        if logits.dim() == 3:
            logits = logits[0]
        if logits.dim() != 2:
            raise ValueError(
                f"logits harus berbentuk (token, label), dapat: {tuple(logits.shape)}"
            )

        sequence_length, num_tags = logits.shape

        if mask is None:
            mask = torch.ones(sequence_length, dtype=torch.long)
        mask = mask.to(torch.bool)
        if mask.shape[0] != sequence_length:
            raise ValueError(
                f"Panjang mask ({mask.shape[0]}) tidak sama dengan jumlah token "
                f"({sequence_length})"
            )

        # Token khusus [CLS]/[SEP] memiliki offset kosong. Keluarkan dulu
        # posisi itu dari Viterbi; kalau ia menjadi posisi pertama dengan
        # skor -inf, seluruh jalur berikutnya juga akan -inf.
        active_indices = torch.nonzero(mask, as_tuple=False).flatten().tolist()
        if not active_indices:
            return [0] * sequence_length
        active_scores = logits[active_indices]
        active_length = active_scores.shape[0]
        best_scores = torch.full((active_length, num_tags), -1e9)
        best_scores[0] = active_scores[0] + self.start_transitions
        backpointers = torch.zeros((active_length, num_tags), dtype=torch.long)

        for step in range(1, active_length):
            # previous[from] + transition[from, to] + score[to] -> skor label "to".
            previous = best_scores[step - 1].unsqueeze(1)
            candidate = previous + self.transitions + active_scores[step].unsqueeze(0)
            best_scores[step], best_previous = torch.max(candidate, dim=0)
            backpointers[step] = best_previous

        best_last = torch.argmax(
            best_scores[active_length - 1] + self.end_transitions
        ).item()
        active_path = [best_last]
        for step in range(active_length - 1, 0, -1):
            active_path.append(backpointers[step, active_path[-1]].item())
        active_path.reverse()

        # Letakkan label kembali ke posisi token asli; token khusus diberi O.
        path = [0] * sequence_length
        for index, label_id in zip(active_indices, active_path):
            path[index] = label_id
        return path
