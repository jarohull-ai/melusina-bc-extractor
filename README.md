# Melusina BC Extractor

Pattern-based behavioral constitution rule extractor for **Jaro Flash Protocol v16E.0.0**.

Detects learning signals in user messages and proposes JFP-formatted rules,
optionally persisting them to `~/.jfp/constitution.jfp`.

## Signal types

| Type | Triggers | Section | Class |
|---|---|---|---|
| EXPLICIT | `od teraz`, `zawsze`, `nigdy`, `pamiętaj że`, `always`, `never`, `remember that` | BEHAVIORAL_RULES / PRIORITIES | ALPHA / BETA |
| DOMAIN | `to się nazywa`, `nasz termin to`, `we call it`, `the term is` | DOMAIN_KNOWLEDGE | GAMMA |
| IMPLICIT | `nie mów`, `wrong:`, `błąd:`, `actually`, `don't say` | BEHAVIORAL_RULES | BETA |

## Usage

```bash
# Interactive mode
python3 extractor.py

# Single message
python3 extractor.py "od teraz zawsze odpowiadaj po polsku"

# Auto-accept (no prompt)
python3 extractor.py --no-confirm "nigdy nie używaj emoji"

# Custom constitution path
python3 extractor.py --constitution /path/to/my.jfp "pamiętaj że projekt to VIKI"
```

## Output format

```json
{
    "section": "BEHAVIORAL_RULES | DOMAIN_KNOWLEDGE | PRIORITIES",
    "key": "RULE_001",
    "value": "treść reguły",
    "class": "ALPHA | BETA | GAMMA",
    "source": "explicit | implicit | domain",
    "timestamp": "2026-06-23T08:00:00+00:00"
}
```

## Tests

```bash
python3 -m pytest test_extractor.py -v
```

## Author
Jarosław Kuchta — JFP / VIKI ecosystem
