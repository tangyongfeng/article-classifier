<div align="center">

# 📚 Article Classifier

### Intelligentes LLM-gestütztes Artikelklassifizierungssystem

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

[English](../README.md) | [简体中文](README_CN.md) | [Deutsch](README_DE.md)

</div>

---

## ✨ Funktionen

- 🤖 **KI-gestützte Klassifizierung** - Nutzt LLM zur intelligenten Kategorisierung von Artikeln
- 🌳 **Dynamische Kategoriehierarchie** - Erstellt und optimiert automatisch mehrstufige Kategoriebäume
- 📄 **Mehrformat-Unterstützung** - Verarbeitet HTML-, Markdown- und Textdateien
- 💾 **Duale Speicherung** - PostgreSQL für Metadaten + JSON für vollständige Inhalte
- ⚡ **Stapelverarbeitung** - Effiziente Verarbeitung tausender Artikel
- 🔄 **Auto-Optimierung** - Verfeinert kontinuierlich die Kategoriestruktur basierend auf Inhaltsmustern
- 🎯 **Konfidenz-Scoring** - Weist Klassifizierungen Konfidenzniveaus zu
- 📊 **Umfassendes Logging** - Detaillierte Verarbeitungsprotokolle und Fehlerverfolgung

## 🚀 Schnellstart

### Voraussetzungen

- Python 3.10 oder höher
- PostgreSQL 13 oder höher
- [Ollama](https://ollama.ai/) mit einem kompatiblen LLM-Modell

### Installation

1. **Repository klonen**
   ```bash
   git clone https://github.com/tangyongfeng/article-classifier.git
   cd article-classifier
   ```

2. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **Datenbank einrichten**
   ```bash
   psql -U postgres -f scripts/setup_database.sql
   ```

4. **Umgebungsvariablen konfigurieren**
   ```bash
   cp .env.example .env
   # Bearbeiten Sie .env und setzen Sie Ihr PostgreSQL-Passwort
   ```

5. **System konfigurieren**
   ```bash
   cp config.yaml.example config.yaml
   # config.yaml bei Bedarf anpassen (optional)
   ```

### Verwendung

#### Einzeldatei-Verarbeitung
```bash
python scripts/single_process.py pfad/zum/artikel.html
```

#### Stapelverarbeitung
```bash
# Alle Dateien in einem Verzeichnis verarbeiten
python scripts/batch_process.py --input /pfad/zu/artikeln

# Im Hintergrund ausführen
nohup python scripts/batch_process.py --input /pfad/zu/artikeln > output.log 2>&1 &
```

## 📁 Projektstruktur

```
article-classifier/
├── src/                      # Quellcode
│   ├── core/                # Kern-Klassifizierungsengine
│   │   ├── classifier.py    # Hauptklassifizierer
│   │   ├── llm_service.py   # LLM-Integration
│   │   ├── category_manager.py    # Kategorieverwaltung
│   │   └── category_optimizer.py  # Auto-Optimierung
│   ├── loaders/             # Datei-Loader
│   │   ├── html_loader.py
│   │   ├── markdown_loader.py
│   │   └── text_loader.py
│   ├── storage/             # Speicherschicht
│   │   ├── database.py      # PostgreSQL-Operationen
│   │   ├── json_storage.py  # JSON-Dateioperationen
│   │   └── models.py        # Datenmodelle
│   └── utils/               # Hilfsprogramme
│       ├── config.py        # Konfigurationsverwaltung
│       └── logger.py        # Logging-Utilities
├── scripts/                  # Ausführbare Skripte
│   ├── batch_process.py     # Stapelverarbeitung
│   ├── single_process.py    # Einzeldatei-Verarbeitung
│   ├── test_setup.py        # Setup-Überprüfung
│   └── setup_database.sql   # Datenbankschema
├── docs/                     # Dokumentation
│   ├── USAGE_GUIDE.md       # Detaillierte Bedienungsanleitung
│   ├── README_CN.md         # Chinesisches README
│   └── README_DE.md         # Deutsches README
├── data/                     # Datenverzeichnis (gitignored)
│   ├── json/                # JSON-Speicher
│   ├── logs/                # Verarbeitungsprotokolle
│   └── failed/              # Verfolgung fehlgeschlagener Dateien
├── config.yaml.example       # Konfigurationsvorlage
├── .env.example             # Umgebungsvariablen-Vorlage
└── requirements.txt         # Python-Abhängigkeiten
```

## 🔧 Konfiguration

### Umgebungsvariablen (.env)
```env
POSTGRES_PASSWORD=ihr_sicheres_passwort
OLLAMA_API_KEY=             # Optional für lokales Ollama
```

### Systemkonfiguration (config.yaml)
```yaml
ollama:
  base_url: "http://localhost:11434"
  model: "gpt-oss:20b"
  temperature: 0.3

classifier:
  max_category_levels: 3
  min_confidence: 0.6
  initial_training_size: 100
  optimization_interval: 100
  auto_optimize: true

database:
  host: "localhost"
  port: 5432
  database: "article_classifier"
  user: "article_classifier_user"

storage:
  json_root: "data/json"
  organize_by_date: true
  save_raw_content: true

processing:
  batch_size: 10
  enable_parallel: false
  checkpoint_interval: 100
  log_level: "INFO"
```

## 🎯 Funktionsweise

### Klassifizierungs-Pipeline

1. **Datei-Scanning** - Entdeckt Artikel im Zielverzeichnis
2. **Inhalts-Laden** - Extrahiert Titel, Inhalt und Metadaten
3. **LLM-Analyse** - Sendet Inhalt an LLM zur Kategorisierung
4. **Kategorie-Erstellung** - Erstellt hierarchische Kategorien (bis zu 3 Ebenen)
5. **Speicherung** - Speichert in PostgreSQL und JSON
6. **Optimierung** - Verfeinert Kategoriestruktur alle N Artikel

### Kategorie-Strategie

#### Anfangsphase (Erste 100 Artikel)
- LLM erstellt frei Kategoriestruktur
- Baut organische Hierarchie basierend auf Inhaltsmustern auf
- Etabliert grundlegende Taxonomie

#### Kontinuierliche Klassifizierung (Nach 100 Artikeln)
- Klassifiziert in bestehende Kategorien
- Erstellt neue Kategorien bei Konfidenz < 0,6
- Erhält Kategoriekonsistenz

#### Auto-Optimierung (Alle 100 Artikel)
- **Aufteilen** - Unterteilt Kategorien mit vielen Artikeln
- **Zusammenführen** - Kombiniert Kategorien mit wenigen Artikeln
- **Entwickeln** - Identifiziert aufkommende Themen und erstellt neue Kategorien

## 📊 Datenspeicherung

### PostgreSQL-Schema
```sql
articles              -- Artikel-Metadaten
categories            -- Kategoriehierarchie
keywords              -- Extrahierte Schlüsselwörter
article_categories    -- Artikel-Kategorie-Beziehungen
article_keywords      -- Artikel-Schlüsselwort-Beziehungen
```

### JSON-Struktur
```
data/json/
├── articles/
│   └── YYYY/
│       └── MM/
│           ├── 000001.json
│           └── 000002.json
└── categories.json
```

## 📈 Leistung

- **Verarbeitungsgeschwindigkeit**: 3-6 Sekunden pro Artikel
- **Stapelverarbeitung**: ~2 Stunden für 1.300 Artikel
- **LLM**: Getestet mit gpt-oss:20b auf lokalem Ollama
- **Speicherung**: Effizienter Dual-Storage-Ansatz

## 🔍 Abfragebeispiele

### SQL-Abfragen
```sql
-- Kategoriebaum anzeigen
WITH RECURSIVE category_tree AS (
  SELECT id, name, parent_id, 1 as level
  FROM categories WHERE parent_id IS NULL
  UNION ALL
  SELECT c.id, c.name, c.parent_id, ct.level + 1
  FROM categories c
  JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree ORDER BY level, name;

-- Top-Schlüsselwörter
SELECT keyword, usage_count
FROM keywords
ORDER BY usage_count DESC
LIMIT 20;

-- Artikel nach Kategorie
SELECT a.title, c.name as category
FROM articles a
JOIN article_categories ac ON a.id = ac.article_id
JOIN categories c ON ac.category_id = c.id
WHERE c.name = 'Technologie';
```

### Python-Abfragen
```python
import json
from pathlib import Path

# Kategoriebaum laden
with open('data/json/categories.json') as f:
    categories = json.load(f)

# Artikel nach Kategorie finden
for article_file in Path('data/json/articles').rglob('*.json'):
    with open(article_file) as f:
        data = json.load(f)
        if 'Technologie' in data['classification']['category_path']:
            print(f"{data['metadata']['title']}")
```

## 🛠️ Erweiterte Nutzung

### Benutzerdefinierte LLM-Modelle
Bearbeiten Sie `config.yaml`, um verschiedene Modelle zu verwenden:
```yaml
ollama:
  model: "llama2:70b"  # oder ein anderes Modell
```

### Dateien erneut verarbeiten
```sql
-- Artikel entfernen, um erneut zu verarbeiten
DELETE FROM articles WHERE file_path = '/pfad/zum/artikel.html';
```

### Backup
```bash
# JSON-Dateien sichern
tar -czf backup_$(date +%Y%m%d).tar.gz data/json/

# Datenbank sichern
pg_dump -U postgres article_classifier > backup_$(date +%Y%m%d).sql
```

## 🐛 Fehlerbehebung

### Häufige Probleme

**F: LLM-Verbindung schlägt fehl**
```bash
# Überprüfen Sie, ob Ollama läuft
curl http://localhost:11434/api/tags

# Ollama bei Bedarf starten
ollama serve
```

**F: Datenbankverbindungsfehler**
```bash
# PostgreSQL-Status überprüfen
pg_isready

# Anmeldedaten in .env überprüfen
cat .env
```

**F: Klassifizierungsqualität ist schlecht**
- Passen Sie `temperature` in config.yaml an (niedriger = deterministischer)
- Verwenden Sie ein größeres LLM-Modell
- Erhöhen Sie `initial_training_size` für bessere Kategoriebasis

## 🗺️ Roadmap

- [ ] Web-UI-Dashboard
- [ ] Vektorsuche für ähnliche Artikel
- [ ] Mehrsprachige UI-Unterstützung
- [ ] PDF-Dokumentenunterstützung
- [ ] API-Endpunkte zur Integration
- [ ] Echtzeit-Klassifizierungsdienst
- [ ] Kategorievorschlags-API

## 🤝 Mitwirken

Beiträge sind willkommen! Bitte zögern Sie nicht, einen Pull Request einzureichen.

1. Forken Sie das Repository
2. Erstellen Sie Ihren Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## 📝 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die [LICENSE](../LICENSE)-Datei für Details.

## 🙏 Danksagungen

- Erstellt mit [LangChain](https://langchain.com/)
- Betrieben von [Ollama](https://ollama.ai/)
- Datenbank: [PostgreSQL](https://www.postgresql.org/)

## 📧 Kontakt

Projekt-Link: [https://github.com/tangyongfeng/article-classifier](https://github.com/tangyongfeng/article-classifier)

---

<div align="center">

Mit ❤️ vom Article Classifier Team erstellt

</div>
