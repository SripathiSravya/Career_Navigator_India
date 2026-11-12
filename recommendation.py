from database import norm
import re
EDU = {"phd": 100, "master": 90, "m.tech": 90, "m.sc": 90, "mca": 90, "mba": 85, "b.tech": 75, "b.e": 75, "bachelor": 75, "b.sc": 70, "bca": 70, "diploma": 55, "12th": 40}
EXP = {"Fresher": 40, "1-2 years": 60, "3-5 years": 80, "5+ years": 100}
GENERIC = "Learn the fundamentals of {s}, its core concepts and common tools."
FIELD_FILTERS = {
    "Software and IT": ["information technology", "software", "data & ai", "cloud & infra", "security", "emerging tech", "quality & docs"],
    "Healthcare": ["healthcare", "medical", "pharmacy", "nursing", "diagnostic"],
    "Engineering": ["engineering", "manufacturing", "construction", "skilled trades"],
    "Finance and Banking": ["banking", "finance", "accounting", "insurance"],
    "Agriculture": ["agriculture", "allied", "forestry", "fisher"],
    "Education": ["education", "training", "teaching"],
    "Sales and Marketing": ["sales", "marketing", "retail", "customer"],
    "Transport and Logistics": ["transport", "logistics", "warehouse", "supply chain"],
    "Design and Media": ["design", "media", "animation", "film"],
    "Hospitality and Tourism": ["hospitality", "tourism", "hotel", "food"],
    "Legal Services": ["legal", "law", "judicial"],
}

# A category alone is not enough for field filtering: imported occupation
# classifications can be broad. Require a recognisable occupation title too.
FIELD_TITLE_PATTERNS = {
    "Software and IT": r"\b(software|web|frontend|front.end|backend|back.end|full.stack|programmer|programming|developer|information technology|it support|systems? analyst|data analyst|data scientist|data engineer|machine learning|artificial intelligence|ai engineer|cyber|security analyst|network engineer|network administrator|cloud|devops|database administrator|database developer|qa engineer|test automation|software tester|technical support|system administrator|systems administrator|blockchain|embedded systems|iot developer|computer security specialist)\b",
    "Healthcare": r"\b(doctor|physician|surgeon|nurs(e|ing)|pharmacist|medical|clinical|healthcare|laboratory technician|lab technician|radiolog|physiotherap|paramedic|dentist|midwi(fe|fery))\b",
    "Engineering": r"\b(engineer|engineering|technician|mechanic|mechanical|civil|electrical|electronics|manufacturing|production|quality control|welding|welder|construction|operator)\b",
    "Finance and Banking": r"\b(accountant|accounting|auditor|bank|banking|financial|finance|insurance|tax|actuary|investment|credit analyst)\b",
    "Agriculture": r"\b(agri|agricultur|farmer|farming|horticultur|forestry|fisher|veterinar|dairy|livestock|soil|crop)\b",
    "Education": r"\b(teacher|teaching|educat|lecturer|professor|instructor|trainer|tutor|academic)\b",
    "Sales and Marketing": r"\b(sales|marketing|retail|merchandis|advertis|public relations|brand|business development)\b",
    "Transport and Logistics": r"\b(driver|pilot|transport|logistic|warehouse|supply chain|shipping|dispatch|delivery|freight)\b",
    "Design and Media": r"\b(design|designer|graphic|animation|animator|media|journal|film|photograph|video editor|content creator)\b",
    "Hospitality and Tourism": r"\b(hospitality|hotel|tourism|travel|chef|cook|catering|housekeeping|front office)\b",
    "Legal Services": r"\b(legal|lawyer|advocate|solicitor|judicial|paralegal|law clerk)\b",
}

# Broad/generic titles must not be treated as proof of a field.
GENERIC_TITLES = {"analyst", "operator", "assistant", "officer", "clerk", "worker", "associate", "manager"}
SOFTWARE_EXCLUDED_TITLE_PATTERNS = re.compile(
    r"\b(computer operator|computer clerk|computer typist|data entry operator|office operator|office assistant|clerical operator|computer system hardware|hardware analyst|hardware engineer|computer topographical|topographical|topographic|cartographic|computer cartography)\b", re.I
)

def _matches_career_field(career, career_field):
    if not career_field or career_field == "All Career Fields":
        return True
    title = (career["name"] or "").strip().lower()
    category = (career["category"] or "").strip().lower()
    allowed_categories = FIELD_FILTERS.get(career_field, [])
    category_match = any(term in category for term in allowed_categories)
    pattern = FIELD_TITLE_PATTERNS.get(career_field)
    title_match = bool(pattern and re.search(pattern, title, re.I))
    # For software/IT, require a specific IT occupation title as well as
    # the expected domain category; generic titles never pass on category alone.
    if career_field == "Software and IT":
        # Do not treat clerical/computer-operation occupations as IT careers
        # merely because their title contains the word "computer".
        if title in GENERIC_TITLES or SOFTWARE_EXCLUDED_TITLE_PATTERNS.search(title):
            return False
        strong_it_title = bool(re.search(
            r"\b(software|web|frontend|front.end|backend|back.end|full.stack|programmer|developer|data analyst|data scientist|data engineer|machine learning|artificial intelligence|cybersecurity|cyber security|security specialist|network engineer|network administrator|cloud engineer|devops|database administrator|database developer|qa engineer|test automation|software tester|system administrator|systems administrator|application maintenance|application support|it support|information technology|computer security)\b",
            title, re.I))
        return title_match and (category_match or strong_it_title)
    if title in GENERIC_TITLES:
        return False
    return title_match and (category_match or bool(pattern and re.search(pattern, title, re.I)))

# Curated, occupation-specific technical skill requirements for common roles.
# These override broad family-level placeholder skills imported from NCO.
# Unmapped occupations retain their source-derived skills, but generic titles
# are excluded from ranked recommendations until they can be classified.
OCCUPATION_SKILLS = {
    "web developer": [("HTML",5),("CSS",5),("JavaScript",5),("Git",3),("Responsive Design",3),("APIs",3)],
    "frontend developer": [("HTML",5),("CSS",5),("JavaScript",5),("React",4),("Git",3),("Responsive Design",3)],
    "backend developer": [("Python",5),("SQL",5),("APIs",5),("Git",3),("Node.js",4),("Databases",4)],
    "full stack developer": [("HTML",4),("CSS",4),("JavaScript",5),("React",4),("Node.js",4),("SQL",4)],
    "software engineer": [("Programming",5),("Data Structures",5),("Algorithms",5),("OOP",4),("Git",3),("SQL",3)],
    "application maintenance engineer": [("Java",4),("SQL",4),("Linux",4),("APIs",3),("Debugging",5),("Application Support",5)],
    "associate network engineer": [("Networking",5),("TCP/IP",5),("Routing and Switching",5),("Linux",3),("Network Security",4),("Troubleshooting",4)],
    "network engineer": [("Networking",5),("TCP/IP",5),("Routing and Switching",5),("Linux",3),("Network Security",4),("Troubleshooting",4)],
    "network administrator": [("Networking",5),("TCP/IP",5),("Network Administration",5),("Linux",3),("Network Security",4),("Troubleshooting",4)],
    "data analyst": [("SQL",5),("Excel",4),("Python",4),("Power BI",4),("Statistics",4),("Data Visualization",4)],
    "data scientist": [("Python",5),("Statistics",5),("Machine Learning",5),("SQL",4),("Pandas",4),("Data Visualization",3)],
    "database administrator": [("SQL",5),("Database Administration",5),("MySQL",4),("PostgreSQL",4),("Backup and Recovery",4),("Linux",3)],
    "cybersecurity analyst": [("Cybersecurity",5),("Networking",4),("Linux",4),("SIEM",4),("Incident Response",5),("Python",3)],
    "computer security specialist": [("Cybersecurity",5),("Networking",4),("Linux",4),("Security Auditing",4),("Incident Response",5),("Access Control",4)],
    "devops engineer": [("Linux",5),("Docker",5),("CI/CD",5),("Git",4),("Kubernetes",4),("AWS",4)],
    "cloud engineer": [("AWS",5),("Linux",4),("Networking",4),("Docker",4),("Cloud Computing",5),("Terraform",4)],
    "qa engineer": [("Software Testing",5),("Test Automation",5),("Selenium",4),("Java",3),("SQL",3),("Jira",2)],
    "mobile app developer": [("Kotlin",5),("Java",4),("Android",5),("APIs",3),("Git",3),("UI Design",2)],
}
GENERIC_OR_UNCLEAR = {
    "analyst", "operator", "assistant", "officer", "clerk", "worker", "associate",
    "manager", "computer network professionals, other", "network professionals, other",
}

def _occupation_skills(career, stored_rows, career_field="All Career Fields"):
    name = re.sub(r"\s+", " ", (career["name"] or "").strip().lower())
    # Exact curated mapping first.
    if name in OCCUPATION_SKILLS:
        return OCCUPATION_SKILLS[name]
    # Keep ambiguous NCO catch-all titles out of recommendations.
    if name in GENERIC_OR_UNCLEAR or re.search(r",\s*other$|\b(other|not elsewhere classified|n\.e\.c\.)\b", name):
        return None
    # For common IT titles with modifiers (e.g. Senior Backend Developer),
    # use the closest curated role mapping.
    for key, values in OCCUPATION_SKILLS.items():
        if key in name:
            return values
    # In the Software and IT shortlist, do not reuse broad NCO family skills
    # for an unfamiliar title. Those generic mappings caused unrelated jobs
    # to score highly on common skills such as Java, Python and SQL.
    if career_field == "Software and IT":
        return None
    return [(r["skill"], r["weight"]) for r in stored_rows]

def recommend(db, user_skills, top=5, career_field="All Career Fields"):
    us = {norm(s) for s in user_skills}; out = []
    careers = db.execute("SELECT * FROM careers WHERE status='Active'").fetchall()
    for c in careers:
        if not _matches_career_field(c, career_field):
            continue
        stored = db.execute("SELECT skill,weight FROM career_skills WHERE career_id=? ORDER BY weight DESC,skill", (c["id"],)).fetchall()
        skill_rows = _occupation_skills(c, stored, career_field)
        if not skill_rows:
            continue
        # De-duplicate skill labels after alias normalisation.
        deduped, seen = [], set()
        for skill, weight in skill_rows:
            key = norm(skill)
            if key and key not in seen:
                seen.add(key); deduped.append((skill, weight))
        if not deduped:
            continue
        tot = sum(weight for _, weight in deduped)
        matched = [skill for skill, _ in deduped if norm(skill) in us]
        missing = [(skill, weight) for skill, weight in deduped if norm(skill) not in us]
        got = sum(weight for skill, weight in deduped if norm(skill) in us)
        pct = round(100 * got / tot, 1) if tot else 0
        # Do not recommend a career with no matched required skill. This prevents
        # arbitrary imported records from filling the top-N list.
        if not matched:
            continue
        roles = [r["title"] for r in db.execute("SELECT title FROM career_roles WHERE career_id=? LIMIT 6", (c["id"],))]
        why = f"You match {len(matched)} of {len(deduped)} required skills ({pct}% of the weighted requirement)."
        why += " Strongest matches: " + ", ".join(matched[:3]) + "."
        if missing:
            why += f" Most important gap: {missing[0][0]}."
        out.append(dict(id=c["id"], name=c["name"], category=c["category"], pct=pct,
                        matched=matched, missing=missing, roles=roles, why=why,
                        nskills=len(deduped), skill_pct=round(100 * len(matched) / len(deduped), 1)))
    out.sort(key=lambda x: (-x["pct"], -len(x["matched"]), x["name"].lower()))
    return out[:top]
# Skill-specific learning plans. Each entry contains concrete topics, exercises,
# a project and a measurable outcome instead of repeating a generic template.
ROADMAPS = {
    "python": ("Python syntax, variables, data types, conditions, loops, functions, collections, files, exceptions and modules.", "Write a calculator, a file reader, 10 list/dictionary exercises and 5 function-based problems.", "Build a command-line expense tracker that saves and searches records in a CSV or JSON file.", "You can write and debug a small Python application using functions, collections and file handling."),
    "javascript": ("Variables (let/const), data types, operators, conditions, loops, functions, arrays, objects, DOM selection, events, promises, fetch and async/await.", "Solve array and string problems; build a form validator; handle button clicks and fetch data from a public JSON endpoint.", "Create an interactive task manager with add, edit, delete, filter and local-storage features.", "You can build interactive browser features and work with asynchronous JavaScript."),
    "react": ("JSX, components, props, state, event handling, conditional rendering, lists and keys, forms, hooks (useState/useEffect), API calls and component composition.", "Build reusable cards, a controlled form, a searchable list and a component that loads API data.", "Create a React job-tracker dashboard with reusable components, filters and persistent task status.", "You can structure a frontend application into reusable React components and manage its state."),
    "html": ("Semantic HTML, document structure, headings, links, images, lists, tables, forms, labels, input types and accessibility attributes.", "Recreate a profile page, a data table and an accessible registration form; validate the page structure.", "Build the complete semantic structure for a personal portfolio with projects and contact sections.", "You can create accessible, well-structured web pages."),
    "css": ("Selectors, cascade, box model, units, typography, colors, Flexbox, Grid, positioning, responsive breakpoints and transitions.", "Recreate a card layout, responsive navigation bar and two-column dashboard at mobile and desktop widths.", "Style a responsive portfolio or career dashboard that works on phone, tablet and desktop.", "You can produce consistent responsive layouts without relying on fixed page widths."),
    "sql": ("SELECT, WHERE, ORDER BY, GROUP BY, aggregate functions, joins, subqueries, constraints, indexes and transactions.", "Write queries for filtering, grouping and joining sample employee, course and order tables.", "Design a small placement database and write queries for student, skill and job-match reports.", "You can retrieve and summarize relational data and explain basic query performance."),
    "java": ("Java syntax, primitive/reference types, control flow, methods, arrays, classes, objects, inheritance, interfaces, exceptions and collections.", "Solve loop and array problems; implement classes; practise inheritance, interfaces and collection operations.", "Build a console-based library management application using classes and collections.", "You can write object-oriented Java programs and handle common runtime errors."),
    "c": ("Variables, data types, operators, conditions, loops, functions, arrays, strings, pointers, structures and file handling.", "Trace pointer examples, implement sorting/searching and practise string and structure programs.", "Build a student-record manager that stores and retrieves records from a file.", "You can write procedural C programs and use pointers and structures safely."),
    "c++": ("C++ syntax, functions, references, classes, constructors, inheritance, polymorphism, STL containers, algorithms and memory basics.", "Implement stack, queue and linked-list exercises; solve problems using vector, map and algorithms.", "Build a console-based inventory manager using classes and STL containers.", "You can write object-oriented C++ and select suitable STL data structures."),
    "sql server": ("T-SQL queries, joins, grouping, views, stored procedures, indexes, transactions and execution plans.", "Create tables and practise joins, stored procedures and query tuning on sample data.", "Build a small reporting database with stored procedures and indexed search queries.", "You can query and maintain a SQL Server database for a small application."),
    "mysql": ("Database creation, data types, primary/foreign keys, CRUD, joins, grouping, indexes, normalization and transactions.", "Create related tables and practise CRUD, joins and aggregate reports.", "Build a course-registration database with constraints and reports.", "You can design and query a normalized MySQL database."),
    "postgresql": ("Schemas, data types, constraints, joins, CTEs, indexes, transactions, views and basic query plans.", "Write multi-table joins, CTE reports and test how indexes affect common queries.", "Create a placement-management database with views for student skills and employer requirements.", "You can model relational data and write maintainable PostgreSQL queries."),
    "node.js": ("Node.js runtime, npm, modules, asynchronous programming, Express routes, middleware, validation and database access.", "Create REST endpoints, validate request bodies and handle errors with middleware.", "Build a REST API for a task manager with CRUD routes and database persistence.", "You can create and test a basic backend API with Node.js and Express."),
    "apis": ("HTTP methods, status codes, headers, JSON, REST resource design, request validation, authentication concepts and error responses.", "Call a public API, inspect responses and implement GET, POST, PUT and DELETE endpoints.", "Build and document a REST API for managing projects or job applications.", "You can integrate an API and design predictable REST endpoints."),
    "git": ("Repositories, working tree, staging, commits, branches, merges, remotes, pull requests and resolving simple conflicts.", "Practise branching, merging and reverting changes in a sample repository.", "Publish one of your learning projects on GitHub with a README and meaningful commit history.", "You can collaborate through Git and maintain a readable project history."),
    "data structures": ("Arrays, linked lists, stacks, queues, hash maps, trees, heaps, graphs and time/space complexity.", "Implement each structure and solve beginner problems involving searching, sorting and traversal.", "Create a visual or menu-driven data-structure demonstrator and document operation complexities.", "You can choose suitable data structures and explain their trade-offs."),
    "algorithms": ("Big-O, searching, sorting, recursion, two pointers, sliding window, greedy methods, divide-and-conquer and graph traversal.", "Solve progressively harder problems and explain the time and space complexity of each solution.", "Build a collection of 20 documented problem solutions grouped by technique.", "You can select and analyse common algorithms for coding problems."),
    "machine learning": ("Supervised vs unsupervised learning, data cleaning, train/test split, regression, classification, clustering, evaluation metrics and overfitting.", "Train baseline models on a small dataset; compare accuracy, precision/recall or RMSE as appropriate.", "Build an end-to-end prediction notebook with preprocessing, model comparison and evaluation.", "You can train, evaluate and explain a basic machine-learning model."),
    "pandas": ("Series and DataFrames, reading files, selecting rows/columns, missing values, filtering, groupby, merge and exporting.", "Clean a messy CSV, group records and combine two related datasets.", "Create a data-cleaning notebook that produces a concise summary report from a public dataset.", "You can clean, transform and summarize tabular data with pandas."),
    "statistics": ("Mean, median, variance, standard deviation, distributions, sampling, confidence intervals, hypothesis tests and correlation.", "Calculate descriptive statistics and interpret simple confidence intervals and hypothesis-test results.", "Analyse a public dataset and write a short report explaining patterns and uncertainty.", "You can interpret common statistical summaries and avoid unsupported conclusions."),
    "power bi": ("Importing data, Power Query, relationships, data modelling, DAX measures, filters, slicers and dashboard design.", "Clean a dataset, create relationships and practise measures such as totals, averages and year-over-year change.", "Build an interactive sales or placement dashboard with KPI cards and drill-down filters.", "You can transform data and communicate findings through an interactive Power BI report."),
    "excel": ("Cell references, tables, sorting/filtering, IF, SUMIFS, COUNTIFS, lookup functions, PivotTables and charts.", "Clean a spreadsheet, use lookup and conditional formulas, then summarize it with a PivotTable.", "Create a placement or expense tracker with formulas, PivotTables and a dashboard chart.", "You can organize, analyse and present structured data in Excel."),
    "docker": ("Images, containers, Dockerfiles, build/run commands, ports, volumes, environment variables and Compose basics.", "Containerize a small web app, map its port and persist one data directory with a volume.", "Package a web application and its database service using Docker Compose.", "You can build and run a repeatable containerized development environment."),
    "linux": ("Filesystem navigation, permissions, processes, pipes, grep, find, package management, shell scripting and logs.", "Practise file operations, permissions, process inspection and text filtering from the terminal.", "Write a shell script that backs up a folder and records a timestamped log.", "You can navigate and troubleshoot a Linux environment using core commands."),
    "aws": ("Cloud regions, IAM basics, compute, storage, networking, security groups, monitoring and cost awareness.", "Deploy a small static site or test app and practise least-privilege access and basic monitoring.", "Deploy a small web application with documented architecture and a cost-conscious configuration.", "You can explain core AWS services and deploy a simple application safely."),
    "networking": ("OSI/TCP-IP models, IP addressing, subnet basics, DNS, DHCP, routing, ports, TCP/UDP and common troubleshooting tools.", "Use ping, traceroute, ipconfig/ifconfig and nslookup; map a small network and identify common ports.", "Create a network diagram and troubleshooting guide for a small office network.", "You can explain basic network communication and troubleshoot common connectivity issues."),
    "cybersecurity": ("Security principles, threat modelling, common vulnerabilities, authentication, access control, encryption basics, logging and incident response.", "Use a legal practice lab to identify common web risks and document mitigations; review sample security logs.", "Prepare a security assessment report for a deliberately vulnerable local practice application.", "You can identify common security risks and recommend basic defensive controls."),
    "figma": ("Frames, layers, components, auto layout, constraints, typography, color styles, prototyping and developer handoff.", "Recreate two mobile screens, build reusable components and connect them in a clickable prototype.", "Design a small mobile app flow with a component library and interactive prototype.", "You can create consistent interface mockups and communicate design behaviour."),
    "selenium": ("WebDriver setup, locators, waits, browser actions, assertions, page objects, test data and screenshots.", "Automate login, form submission and table checks on a permitted practice site.", "Create a small automated regression suite with reusable page objects and clear test reports.", "You can automate repeatable browser checks and diagnose failing tests."),
    "tensorflow": ("Tensors, datasets, model layers, loss functions, optimizers, training loops, validation and saving/loading models.", "Train a small classification model and compare training versus validation performance.", "Build a documented image or tabular classification project with evaluation results.", "You can build and evaluate a basic neural-network model with TensorFlow."),
    "pytorch": ("Tensors, autograd, datasets, DataLoaders, nn.Module, loss functions, optimizers and training/evaluation loops.", "Implement a small neural network and track loss and accuracy across training epochs.", "Build a reproducible classification notebook with saved model weights and evaluation.", "You can implement and train a basic neural network using PyTorch."),
    "nlp": ("Text cleaning, tokenization, normalization, vectorization, embeddings, classification and evaluation.", "Prepare text data, compare bag-of-words and TF-IDF features and evaluate a simple classifier.", "Build a text-classification project such as topic or support-ticket categorization.", "You can prepare text data and evaluate a basic NLP pipeline."),
    "typescript": ("Types, interfaces, unions, functions, generics, narrowing, modules and TypeScript with a frontend framework.", "Convert JavaScript functions to typed versions and model API responses with interfaces.", "Build a typed frontend feature that consumes an API and handles loading/error states.", "You can use TypeScript to catch common data-shape and interface errors."),
    "flutter": ("Dart basics, widgets, layout, navigation, state management, forms, async/await and API integration.", "Build reusable widgets, navigate between screens and load sample JSON data.", "Create a simple mobile habit tracker with forms, navigation and local persistence.", "You can build a multi-screen Flutter app with basic state and data handling."),
    "kubernetes": ("Pods, Deployments, Services, ConfigMaps, Secrets, namespaces, probes, scaling and kubectl basics.", "Deploy a sample container, expose it with a Service and inspect logs and rollout status.", "Create Kubernetes manifests for a small web app and document deployment and rollback steps.", "You can deploy and inspect a basic containerized application on Kubernetes."),
}

def roadmap(db, recs, limit=12):
    """Build a roadmap from each recommended career's actual missing skills."""
    seen, items = set(), []
    for r in recs:
        for skill, weight in r["missing"]:
            key = norm(skill)
            if key in seen:
                continue
            seen.add(key)
            row = db.execute("SELECT * FROM learning_resources WHERE lower(skill)=lower(?)", (skill,)).fetchone()
            plan = ROADMAPS.get(key)
            if row:
                topic, practice, project, outcome = row["topic"], row["practice"], row["project"], row["outcome"]
                link = row["link"]
                source = "database"
            elif plan:
                topic, practice, project, outcome = plan
                link = None
                source = "skill-specific"
            else:
                # Still tailor unknown skills to their career context and importance.
                topic = (f"Study {skill} in the context of {r['name']}: understand its purpose, core concepts, common tools, "
                         f"typical workflow, inputs and outputs, and how professionals use it in real tasks.")
                practice = (f"Complete a guided beginner exercise for {skill}; repeat it without instructions; then solve "
                            f"two problems that use {skill} in a {r['name']} scenario. Document errors and fixes.")
                project = (f"Create a small {r['name']} portfolio task that uses {skill} to solve one clearly defined problem. "
                           f"Include setup steps, sample input/output, screenshots or results, and a README.")
                outcome = (f"You can demonstrate {skill} in a {r['name']} task, explain the decisions you made, and show a working project.")
                link = None
                source = "career-tailored"
            items.append(dict(skill=skill, career=r["name"], weight=weight, topic=topic,
                              practice=practice, project=project, outcome=outcome,
                              link=link, custom=True, plan_type=source))
    return items[:limit]

def resume_quality(text, n_skills):
    low = text.lower(); has = lambda *k: any(x in low for x in k); words = len(text.split())
    checks = [("Enough text content", 20 if words >= 150 else 10 if words >= 60 else 0, 20, "Add more detail; aim for at least 150 words."),
      ("Education information", 15 if has("education", "university", "college", "b.tech", "bachelor", "master") else 0, 15, "Add an Education section."),
      ("Experience, internships or projects", 15 if has("experience", "internship", "project") else 0, 15, "Add projects or internships with outcomes."),
      ("Skills section", 10 if has("skills") else 0, 10, "Add a clear Skills section."),
      ("Recognised technical skills", 20 if n_skills >= 5 else 10 if n_skills >= 3 else 0, 20, "List more relevant technical skills (5 or more)."),
      ("Contact details", (5 if "@" in text else 0) + (5 if sum(c.isdigit() for c in text) >= 10 else 0), 10, "Include email and phone number."),
      ("Certifications or achievements", 10 if has("certif", "award", "achievement", "hackathon") else 0, 10, "Add certifications or achievements.")]
    return dict(score=sum(c[1] for c in checks), words=words, strengths=[c[0] for c in checks if c[1] == c[2]],
                improve=[c[3] for c in checks if c[1] < c[2]])
def readiness(skills, edu, exp, top, text):
    tech = min(100, len(skills) * 10); rel = top["pct"] if top else 0
    ed = max([v for k, v in EDU.items() if k in edu.lower()] or [50])
    ex = min(100, EXP.get(exp, 40) + (20 if "project" in text.lower() and exp == "Fresher" else 0))
    parts = [("Technical skills (10 skills = 100%)", tech, 30), ("Relevance to top career", rel, 35), ("Education", ed, 15), ("Experience (freshers get credit for projects)", ex, 20)]
    score = round(sum(p * w for _, p, w in parts) / 100, 1)
    return dict(score=score, parts=[(n, round(p), w) for n, p, w in parts], strengths=[n for n, p, w in parts if p >= 70],
                improve=[n for n, p, w in parts if p < 50],
                tips=["Build 2 to 3 projects that use your target career's skills.", "Learn the highest-weighted missing skills first.", "Add internships, certifications or open-source work."])
def guidance(name, edu, exp, recs, rd):
    if not recs: return ["No career categories are currently available. Please try again after the career database is initialized."]
    t = recs[0]; miss = [m[0] for m in t["missing"][:3]]; g = []
    g.append(f"Focus on {t['name']} first: it is your best match at {t['pct']}%." + (f" {recs[1]['name']} is a good second option." if len(recs) > 1 else ""))
    g.append("Learn these first: " + ", ".join(miss) + "." if miss else "You cover all required skills for this career; deepen them with advanced projects.")
    g.append(f"Build a project that uses {', '.join(miss[:2]) or ', '.join(t['matched'][:2])} and publish it on GitHub.")
    g.append("As a fresher, internships and projects matter most." if exp == "Fresher" else f"Highlight your {exp} of experience with measurable results.")
    g.append(f"Your job-readiness score is {rd['score']}%. " + ("Keep applying and refine your resume." if rd["score"] >= 70 else "Close skill gaps before mass applying."))
    g.append(f"Next step: finish the roadmap, update your resume ({edu or 'education'} section included) and apply to entry-level roles.")
    return g
