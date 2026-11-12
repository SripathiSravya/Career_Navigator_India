# Career Navigator — India-focused career catalogue

Career Navigator is a Flask-based career recommendation project. Its career catalogue is designed around Indian occupations rather than European occupation data or foreign job-board feeds.

## Indian career data sources

- **Primary source — Directorate General of Employment (DGE), Government of India: NCO 2015.** The application reads the official searchable occupation catalogue at https://www.dge.gov.in/nat and imports occupation titles, NCO codes, and their division, sub-division, group, and family classification.
- **Supplementary reference — National Skill Development Corporation (NSDC).** The application checks the official National Occupational Standards and Model Curriculum catalogue at https://www.nsdcindia.org/national-occupational-standards-and-model-curriculum. NSDC qualification packs and NOS are industry-linked job-role and skill references. The current importer does not claim to have downloaded every NSDC qualification pack or every job role from linked external portals.

NCO 2015 is a broad official Indian occupation classification. The Government of India describes it as covering approximately 3,600 civilian occupations across 52 sectors. It is a classification, not a live vacancy feed. It is revised periodically, not every time a company creates a new job title.

## How the database grows

1. On startup, the background synchroniser checks the official DGE NCO occupation catalogue.
2. It reads the paginated occupation table and imports new occupation titles and their Indian classification details into SQLite.
3. Existing career names are not duplicated. New records receive starter skill mappings based on their occupational family; these mappings are intended for project matching and should be reviewed for accuracy.
4. The recommendation engine loops through all active career records in SQLite. There is no fixed 25-career recommendation limit.
5. A successful catalogue check is cached for 24 hours. Failed checks are retried by the scheduler approximately every 15 minutes while the Flask process is running.

## Important accuracy and hosting notes

- No public source can guarantee a complete list of every career currently present in India or detect every newly coined job title immediately.
- NCO 2015 is the broad baseline; emerging roles not yet listed in NCO can be added only when a trusted Indian source publishes them and the importer is configured to read that source.
- NSDC publishes and revises Qualification Packs/National Occupational Standards, but the current code checks its official catalogue page; it does not claim that all linked QP/NOS files have been parsed into individual career records.
- This project does not use ESCO or foreign job-board feeds as its career database.
- The background scheduler runs inside the Flask/Gunicorn process. On free hosting platforms that sleep or restart services, a 24-hour check is best-effort and cannot be guaranteed to run at an exact time. For guaranteed scheduled updates, use an always-on service or an external scheduled job.
- If the DGE site changes its page layout, the HTML table parser may need updating. If the source is temporarily unavailable, the app continues using the careers already stored in SQLite.

## Run locally (Windows / VS Code)

```bash
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000/.

The terminal should show `[INDIA NCO/NSDC]` messages when the catalogue synchroniser runs. The first attempt starts shortly after the app starts; it may take time because the official NCO catalogue is paginated.

## Deployment

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Keep your database file or configure a persistent database/disk before replacing a deployed project. Some free hosting filesystems are ephemeral.


## Preferred career field filtering
The profile form includes a Preferred career field selector. Selecting a field filters recommendations to matching Indian occupation categories; selecting All Career Fields searches all active careers. All imported occupations remain in the database. The category mapping is based on the occupation category assigned during catalogue import, so some broad or uncategorised NCO entries may not appear under a narrow field until their category mapping is improved.
# Career_Navigator_India
India-focused Career Navigation and Job Recommendation System
