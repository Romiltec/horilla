# Guida al Deploy di Horilla HRMS

Guida completa per il deploy di Horilla HRMS con Docker.

---

## Indice

1. [Prerequisiti](#1-prerequisiti)
2. [Avvio Rapido](#2-avvio-rapido)
3. [Configurazione Ambiente (.env)](#3-configurazione-ambiente-env)
4. [Architettura Docker](#4-architettura-docker)
5. [Inizializzazione Database](#5-inizializzazione-database)
6. [Comandi Utili](#6-comandi-utili)
7. [Produzione](#7-produzione)
8. [Volumi e Persistenza](#8-volumi-e-persistenza)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisiti

- **Docker** >= 24.0 e **Docker Compose** >= 2.20 (incluso in Docker Desktop)
- **Git**

Verifica l'installazione:

```bash
docker --version
docker compose version
git --version
```

---

## 2. Avvio Rapido

```bash
# Clonare il repository
git clone https://github.com/Romiltec/horilla.git
cd horilla
git checkout feature/italian-docker

# Creare il file di configurazione
cp .env.example .env

# Modificare .env con i propri valori (vedi sezione 3)
# OBBLIGATORIO: cambiare SECRET_KEY, POSTGRES_PASSWORD e REDIS_PASSWORD

# Avviare i servizi
docker compose up -d
```

Al primo avvio, l'entrypoint esegue automaticamente:
1. Attesa della disponibilita di PostgreSQL
2. Migrazioni del database (`migrate`)
3. Compilazione delle traduzioni (`compilemessages`)
4. Raccolta dei file statici (`collectstatic`)

Accedere all'applicazione: **http://localhost:8000**

---

## 3. Configurazione Ambiente (.env)

Copiare `.env.example` in `.env` e personalizzare i valori.

### Variabili obbligatorie

| Variabile | Descrizione | Esempio |
|-----------|-------------|---------|
| `SECRET_KEY` | Chiave segreta Django (minimo 50 caratteri) | Generare con il comando sotto |
| `POSTGRES_PASSWORD` | Password del database PostgreSQL | `una-password-robusta-123` |
| `REDIS_PASSWORD` | Password di Redis | `altra-password-robusta-456` |

Generare una `SECRET_KEY` sicura:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

oppure, se non si ha Python installato localmente:

```bash
docker run --rm python:3.12-slim python -c \
  "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Variabili opzionali

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `DEBUG` | `0` | `1` per abilitare la modalita debug (solo sviluppo) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Host consentiti, separati da virgola |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Origini CSRF fidate |
| `CORS_ALLOWED_ORIGINS` | - | Origini CORS consentite |
| `LANGUAGE_CODE` | `it` | Codice lingua (es. `it`, `en`, `de`) |
| `TIME_ZONE` | `Europe/Rome` | Fuso orario |
| `DB_INIT_PASSWORD` | - | Password per il caricamento dati demo |
| `GUNICORN_WORKERS` | auto (2*CPU+1, max 8) | Numero di worker Gunicorn |
| `GUNICORN_LOG_LEVEL` | `info` | Livello log (`debug`, `info`, `warning`, `error`) |
| `GUNICORN_RELOAD` | `false` | `true` per il reload automatico (solo sviluppo) |

### Variabili HTTPS (produzione)

Decommentare nel `.env` quando si utilizza HTTPS:

| Variabile | Descrizione |
|-----------|-------------|
| `SECURE_SSL_REDIRECT` | Redirect automatico da HTTP a HTTPS |
| `SESSION_COOKIE_SECURE` | Cookie di sessione solo su HTTPS |
| `CSRF_COOKIE_SECURE` | Cookie CSRF solo su HTTPS |
| `SECURE_HSTS_SECONDS` | Durata HSTS in secondi (31536000 = 1 anno) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Applicare HSTS anche ai sottodomini |
| `SECURE_HSTS_PRELOAD` | Abilitare HSTS preload |

---

## 4. Architettura Docker

Il progetto utilizza 4 servizi definiti in `docker-compose.yml`:

```
                    +----------------+
                    |     nginx      |  :80 (solo produzione)
                    |  reverse proxy |
                    +-------+--------+
                            |
                    +-------v--------+
                    |      web       |  :8000
                    | Django+Gunicorn|
                    +---+--------+---+
                        |        |
              +---------v--+  +--v---------+
              |     db     |  |   redis    |
              | PostgreSQL |  |  Redis 7   |
              |    16      |  |            |
              +------------+  +------------+
               :5433->5432     :6380->6379
```

### Dettaglio servizi

| Servizio | Immagine | Porta esterna | Porta interna | Descrizione |
|----------|----------|:---:|:---:|-------------|
| **web** | Build da `Dockerfile` | 8000 | 8000 | Django con Gunicorn (gthread, 4 thread per worker) |
| **db** | `postgres:16-alpine` | 5433 | 5432 | Database PostgreSQL con persistenza su volume |
| **redis** | `redis:7-alpine` | 6380 | 6379 | Cache e broker, con persistenza AOF |
| **nginx** | `nginx:alpine` | 80 | 80 | Reverse proxy, serve file statici e media (solo profilo `production`) |

**Nota sulle porte**: Le porte esterne (`5433`, `6380`) sono mappate su valori non standard per evitare conflitti con eventuali istanze locali di PostgreSQL e Redis.

### Dettaglio container web

Il container `web` utilizza un Dockerfile multi-stage:
- **Stage builder**: compila le dipendenze Python in un virtualenv
- **Stage production**: immagine minimale con solo le librerie runtime
- Esegue come utente non-root (`appuser`, UID 1000)
- Healthcheck ogni 30 secondi su `/health/`

---

## 5. Inizializzazione Database

Al primo avvio le migrazioni vengono eseguite automaticamente. Per popolare il database ci sono due opzioni:

### A. Setup Guidato (consigliato)

Navigare a:

```
http://localhost:8000/initialize-database/
```

Questa interfaccia guida nella creazione dell'azienda, del primo superutente e della configurazione iniziale.

### B. Caricamento Dati Demo

Per caricare un dataset dimostrativo gia popolato:

1. Assicurarsi che `DB_INIT_PASSWORD` sia impostato nel file `.env`
2. Navigare a:

```
http://localhost:8000/load-demo-database/
```

3. Inserire la password configurata in `DB_INIT_PASSWORD`

**Attenzione**: il caricamento dei dati demo sovrascrive eventuali dati esistenti.

---

## 6. Comandi Utili

### Gestione servizi

```bash
# Avviare tutti i servizi
docker compose up -d

# Fermare tutti i servizi
docker compose down

# Riavviare un servizio specifico
docker compose restart web

# Vedere lo stato dei servizi
docker compose ps

# Vedere i log in tempo reale
docker compose logs -f web

# Vedere i log di tutti i servizi
docker compose logs -f
```

### Gestione applicazione

```bash
# Creare un superutente
docker compose exec web python manage.py createhorillauser

# Backup dei dati
docker compose exec web python manage.py horilladumpdata

# Compilare le traduzioni
docker compose exec web python manage.py compilemessages

# Raccogliere i file statici
docker compose exec web python manage.py collectstatic --noinput

# Eseguire le migrazioni
docker compose exec web python manage.py migrate
```

### Accesso diretto

```bash
# Shell Django (Python)
docker compose exec web python manage.py shell

# Accesso al database PostgreSQL
docker compose exec db psql -U horilla -d horilla

# Shell bash nel container web
docker compose exec web bash
```

### Rebuild

```bash
# Ricostruire l'immagine dopo modifiche al Dockerfile o requirements.txt
docker compose build web

# Ricostruire e riavviare
docker compose up -d --build
```

---

## 7. Produzione

### Checklist pre-produzione

- [ ] Impostare `DEBUG=0`
- [ ] Generare una `SECRET_KEY` unica e robusta
- [ ] Configurare `ALLOWED_HOSTS` con il dominio reale
- [ ] Configurare `CSRF_TRUSTED_ORIGINS` con l'URL completo (`https://miodominio.com`)
- [ ] Configurare `CORS_ALLOWED_ORIGINS` se necessario
- [ ] Impostare password robuste per `POSTGRES_PASSWORD` e `REDIS_PASSWORD`
- [ ] Abilitare le impostazioni HTTPS nel `.env`

### Avvio con Nginx

Per abilitare il reverse proxy Nginx, utilizzare il profilo `production`:

```bash
docker compose --profile production up -d
```

Questo avvia anche il servizio `nginx` sulla porta 80, che:
- Serve i file statici (`/static/`) e media (`/media/`) direttamente
- Fa da proxy verso Gunicorn per le richieste dinamiche
- Imposta gli header `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`
- Limita l'upload a 50MB (`client_max_body_size`)

### Configurazione SSL/HTTPS

Per HTTPS si consiglia di utilizzare un reverse proxy esterno (es. Traefik, Caddy) oppure di modificare `docker/nginx.conf` per includere i certificati SSL.

Dopo aver configurato HTTPS, decommentare nel `.env`:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

---

## 8. Volumi e Persistenza

I dati persistenti sono gestiti tramite volumi Docker denominati:

| Volume | Percorso nel container | Contenuto |
|--------|----------------------|-----------|
| `postgres_data` | `/var/lib/postgresql/data` | File del database PostgreSQL |
| `redis_data` | `/data` | Persistenza Redis (AOF - Append Only File) |
| `staticfiles` | `/app/staticfiles` | File statici raccolti da `collectstatic` |
| `media` | `/app/media` | File caricati dagli utenti (foto profilo, documenti, ecc.) |

### Backup

```bash
# Backup del database
docker compose exec db pg_dump -U horilla horilla > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore del database
docker compose exec -T db psql -U horilla horilla < backup_20240101_120000.sql

# Backup applicativo (tramite management command)
docker compose exec web python manage.py horilladumpdata
```

### Eliminazione dati

```bash
# Fermare i servizi e rimuovere i volumi (ATTENZIONE: cancella tutti i dati)
docker compose down -v
```

---

## 9. Troubleshooting

### Il container web non si avvia

**Sintomo**: il container `web` va in restart loop.

```bash
docker compose logs web
```

**Causa comune**: il database non e ancora pronto. L'entrypoint attende PostgreSQL, ma se il container `db` ha problemi, `web` non partira.

**Soluzione**: verificare i log del database:

```bash
docker compose logs db
```

### Conflitto di porte

**Sintomo**: errore `bind: address already in use`.

Le porte esterne sono gia configurate su valori non standard per evitare conflitti:
- PostgreSQL: **5433** (anziche 5432)
- Redis: **6380** (anziche 6379)

Se anche queste sono occupate, modificare i mapping in `docker-compose.yml`:

```yaml
ports:
  - "5434:5432"  # cambiare la porta esterna
```

### File statici non caricati (404)

**Sintomo**: la pagina appare senza stili CSS o immagini.

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose restart web
```

In produzione con Nginx, verificare che il volume `staticfiles` sia montato correttamente.

### Traduzioni non visualizzate

**Sintomo**: l'interfaccia mostra testi in inglese anziche in italiano.

```bash
docker compose exec web python manage.py compilemessages
docker compose restart web
```

Verificare che nel `.env` sia impostato `LANGUAGE_CODE=it`.

### Errore di connessione al database

**Sintomo**: `django.db.utils.OperationalError: could not connect to server`.

Verificare che:
1. Il container `db` sia in esecuzione: `docker compose ps`
2. La password in `DATABASE_URL` corrisponda a `POSTGRES_PASSWORD`
3. Il database non sia corrotto: `docker compose logs db`

In caso di corruzione, ricreare il volume:

```bash
docker compose down
docker volume rm horilla_postgres_data
docker compose up -d
```

**Attenzione**: questo cancella tutti i dati del database.

### Permessi sui file

**Sintomo**: `PermissionError` nei log.

Il container esegue come `appuser` (UID 1000). Se i volumi montati hanno permessi diversi:

```bash
docker compose exec -u root web chown -R appuser:appuser /app/staticfiles /app/media
```

### Memoria insufficiente

**Sintomo**: il container viene terminato (OOMKilled).

Ridurre il numero di worker Gunicorn nel `.env`:

```env
GUNICORN_WORKERS=2
```

---

## Riferimenti

- [Horilla HRMS - Documentazione ufficiale](https://docs.horilla.com/)
- [Docker Compose - Documentazione](https://docs.docker.com/compose/)
- [Gunicorn - Configurazione](https://docs.gunicorn.org/en/stable/settings.html)
- [Django - Checklist di deploy](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
