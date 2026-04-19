from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Category,
    Certificate,
    CourseLesson,
    CourseNote,
    Coupon,
    Course,
    Enrollment,
    StudentProfile,
    Notification,
    Order,
    PasswordResetToken,
    QuizAttempt,
    Review,
    SiteSetting,
    InterviewDomain,
    InterviewQuestion,
    QuestionTag,
    QuestionTagMap,
    QuestionCompany,
    QuestionCompanyMap,
    QuestionTestCase,
    InterviewTopic,
    StudyPlannerTemplate,
    User,
)
from app.utils.security import hash_password
from app.utils.text import slugify

COURSE_SEED = [
    # ── Python ──────────────────────────────────────────────────────────
    {
        "slug": "python-full-stack-portfolio-track",
        "title": "Python Full Stack Development",
        "thumbnail": "/images/python-logo.png",
        "description": (
            "Master Python Full Stack Development from scratch. This placement-focused program covers "
            "HTML, CSS, JavaScript, React, Python (Flask/Django), REST APIs, SQL, Git, and cloud deployment. "
            "13 structured modules with real-world projects. Roles: Python Developer, API Developer, "
            "Backend Developer, Web Developer. Duration: 3–6 months live interactive."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "Python",
        "instructor": "Priya N",
        "quizzes_count": 13,
        "students_count": 295,
        "rating": 4.8,
    },
    {
        "slug": "python-placement-bootcamp",
        "title": "Python Placement Bootcamp",
        "thumbnail": "/images/python-logo.png",
        "description": (
            "Intensive placement bootcamp covering Python fundamentals, data structures, SQL, "
            "Flask REST APIs, and 100+ interview Q&A sessions. Includes resume grooming, mock interviews, "
            "and dedicated placement cell support. Self-paced option available at Rs.4,999+GST."
        ),
        "price": 35000,
        "discount_price": 14999,
        "category": "Python",
        "instructor": "Priya N",
        "quizzes_count": 10,
        "students_count": 210,
        "rating": 4.7,
    },
    # ── Java ─────────────────────────────────────────────────────────────
    {
        "slug": "java-full-stack-portfolio-track",
        "title": "Java Full Stack Development",
        "thumbnail": "/images/student-learning.png",
        "description": (
            "Enterprise-grade Java Full Stack program covering Core Java, Advanced Java, Spring Boot, "
            "Spring MVC, Hibernate/JPA, REST API development, React/Angular frontend, SQL, Git, Docker, "
            "and AWS deployment. 13 modules with capstone project. Roles: Java Developer, Spring Boot Developer, "
            "Full Stack Java Developer. Duration: 3–6 months."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "Java",
        "instructor": "Karthik M",
        "quizzes_count": 13,
        "students_count": 220,
        "rating": 4.8,
    },
    {
        "slug": "java-spring-job-track",
        "title": "Java Spring Boot Job Track",
        "thumbnail": "/images/student-learning.png",
        "description": (
            "Focused bootcamp on Core Java OOP, Collections, Multithreading, Spring Boot REST APIs, "
            "Spring Security, Spring Data JPA, Hibernate, Maven/Gradle, and interview question banks. "
            "Covers 200+ real Java interview questions across all levels."
        ),
        "price": 22999,
        "discount_price": 16999,
        "category": "Java",
        "instructor": "Karthik M",
        "quizzes_count": 11,
        "students_count": 150,
        "rating": 4.6,
    },
    # ── Oracle ───────────────────────────────────────────────────────────
    {
        "slug": "oracle-database-development-portfolio-track",
        "title": "Oracle Database Development",
        "thumbnail": "/images/oracle-logo.png",
        "description": (
            "Complete Oracle SQL & PL/SQL training covering SQL fundamentals, advanced queries, "
            "joins, subqueries, database objects, PL/SQL blocks, cursors, procedures, functions, "
            "packages, triggers, transaction control, performance tuning, and real-time enterprise scenarios. "
            "Roles: Oracle SQL Developer, PL/SQL Developer, Junior DBA. Duration: 3–4 months."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "Oracle",
        "instructor": "Meena R",
        "quizzes_count": 10,
        "students_count": 170,
        "rating": 4.7,
    },
    {
        "slug": "oracle-sql-plsql-practical",
        "title": "Oracle SQL & PL/SQL Interview Prep",
        "thumbnail": "/images/oracle-logo.png",
        "description": (
            "Targeted interview preparation covering SQL vs PL/SQL, DELETE/TRUNCATE/DROP differences, "
            "JOIN scenarios, set operators, constraints, NULL handling, GROUP BY vs HAVING, "
            "complex query writing, and scenario-based questions asked in TCS, Infosys, Wipro interviews."
        ),
        "price": 17999,
        "discount_price": 12999,
        "category": "Oracle",
        "instructor": "Meena R",
        "quizzes_count": 8,
        "students_count": 140,
        "rating": 4.5,
    },
    # ── AWS ──────────────────────────────────────────────────────────────
    {
        "slug": "aws-cloud-development-portfolio-track",
        "title": "AWS Cloud Computing & DevOps",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "End-to-end AWS program covering Cloud fundamentals, EC2, S3, RDS, DynamoDB, Lambda, "
            "VPC, IAM, CloudFront, Auto Scaling, CodePipeline, CloudFormation, Docker, ECS/EKS, "
            "monitoring (CloudWatch), cost optimization, and a full cloud deployment capstone. "
            "Roles: AWS Cloud Engineer, DevOps Engineer, Solutions Architect. Duration: 4–6 months."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "AWS",
        "instructor": "Surya K",
        "quizzes_count": 13,
        "students_count": 190,
        "rating": 4.8,
    },
    {
        "slug": "aws-devops-career-path",
        "title": "AWS DevOps Career Path",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Focused DevOps track covering CI/CD pipelines, AWS CodeCommit/CodeBuild/CodeDeploy, "
            "Docker containerization, Kubernetes on EKS, Infrastructure as Code with CloudFormation, "
            "serverless computing with Lambda, security best practices, and 150+ DevOps interview questions."
        ),
        "price": 28999,
        "discount_price": 20999,
        "category": "AWS",
        "instructor": "Surya K",
        "quizzes_count": 12,
        "students_count": 155,
        "rating": 4.7,
    },
    # ── Data Analyst ─────────────────────────────────────────────────────
    {
        "slug": "data-analyst-business-intelligence-portfolio-track",
        "title": "Data Analyst & Business Intelligence",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Complete Data Analyst program covering Excel (pivot tables, dashboards), SQL for analysis, "
            "Statistics, Python (NumPy, Pandas, Matplotlib, Seaborn), Power BI/Tableau, "
            "data cleaning, EDA, trend analysis, cohort analysis, and real-world business case studies. "
            "Roles: Data Analyst, Business Intelligence Analyst, MIS Executive. Duration: 3–5 months."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "Data Analyst",
        "instructor": "Lakshmi V",
        "quizzes_count": 13,
        "students_count": 260,
        "rating": 4.8,
    },
    {
        "slug": "data-analyst-foundation",
        "title": "Data Analyst Foundation",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Beginner-friendly foundation course: Excel formulas, SQL basics, descriptive statistics, "
            "Python Pandas for data manipulation, Matplotlib for charts, and creating professional "
            "dashboards in Power BI. Includes a real business dataset project and placement guidance."
        ),
        "price": 24999,
        "discount_price": 17999,
        "category": "Data Analyst",
        "instructor": "Lakshmi V",
        "quizzes_count": 10,
        "students_count": 165,
        "rating": 4.6,
    },
    # ── React / Full Stack ───────────────────────────────────────────────
    {
        "slug": "react-js-development-portfolio-track",
        "title": "React.js Development",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Modern React.js program covering fundamentals, Hooks (useState, useEffect, useRef), "
            "React Router, Context API, Redux Toolkit, REST API integration with Axios, "
            "Styled Components, form handling with Formik/Yup, performance optimization (memo, useMemo), "
            "and deployment on Vercel/AWS. Roles: React Developer, Frontend Engineer, MERN Developer."
        ),
        "price": 35000,
        "discount_price": 25000,
        "category": "Full Stack Training",
        "instructor": "Arun Prakash",
        "quizzes_count": 13,
        "students_count": 300,
        "rating": 4.7,
    },
    {
        "slug": "react-frontend-pro",
        "title": "React Frontend Pro",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Advanced React track: component architecture patterns, state management deep dive, "
            "HOCs, portals, error boundaries, code splitting, lazy loading, TypeScript with React, "
            "testing with Jest/React Testing Library, and CI/CD deployment pipelines."
        ),
        "price": 16999,
        "discount_price": 11999,
        "category": "Full Stack Training",
        "instructor": "Arun Prakash",
        "quizzes_count": 9,
        "students_count": 180,
        "rating": 4.6,
    },
    {
        "slug": "full-stack-mastery",
        "title": "Full Stack Web Development Mastery",
        "thumbnail": "/images/student-learning.png",
        "description": (
            "Comprehensive placement-focused full stack bootcamp combining Python/Java backend, "
            "React frontend, SQL databases, REST API design, Git collaboration, and production deployment. "
            "Includes LMS access, internship certificate, resume support, and dedicated placement cell."
        ),
        "price": 44999,
        "discount_price": 35000,
        "category": "Full Stack Training",
        "instructor": "Arun Prakash",
        "quizzes_count": 18,
        "students_count": 410,
        "rating": 4.8,
    },
    # ── Supplementary ────────────────────────────────────────────────────
    {
        "slug": "interview-dsa-crash-course",
        "title": "Interview DSA Crash Course",
        "thumbnail": "/images/student-learning.png",
        "description": (
            "Intensive DSA prep: arrays, strings, recursion, trees, graphs, dynamic programming, "
            "and backtracking patterns. 150+ LeetCode-style problems with walkthroughs in Python and Java. "
            "Timed mock contests, whiteboard simulations, and company-specific question sets."
        ),
        "price": 14999,
        "discount_price": 8999,
        "category": "Python",
        "instructor": "Surya K",
        "quizzes_count": 15,
        "students_count": 355,
        "rating": 4.8,
    },
    {
        "slug": "placement-communication-hr",
        "title": "Placement Communication & HR Prep",
        "thumbnail": "/images/interview-prep.png",
        "description": (
            "Soft skills and placement readiness: professional resume writing, LinkedIn optimization, "
            "STAR method for behavioural interviews, group discussion techniques, HR round answers, "
            "salary negotiation, and mock panel interviews with senior trainers."
        ),
        "price": 6999,
        "discount_price": 3999,
        "category": "Data Analyst",
        "instructor": "Lakshmi V",
        "quizzes_count": 6,
        "students_count": 280,
        "rating": 4.5,
    },
    {
        "slug": "system-design-interview-masterclass",
        "title": "System Design Interview Masterclass",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "HLD + LLD patterns: scalability, caching, load balancing, database sharding, CAP theorem, "
            "microservices, API gateway design, and 20+ end-to-end system design walkthroughs "
            "(URL shortener, Twitter clone, Uber architecture). Includes mock design interviews."
        ),
        "price": 15999,
        "discount_price": 9999,
        "category": "Full Stack Training",
        "instructor": "Karthik M",
        "quizzes_count": 7,
        "students_count": 145,
        "rating": 4.7,
    },
    {
        "slug": "cloud-sre-primer",
        "title": "Cloud SRE Primer",
        "thumbnail": "/images/career-hero.png",
        "description": (
            "Site Reliability Engineering on AWS: observability with CloudWatch and X-Ray, "
            "incident response playbooks, SLO/SLA/SLI definitions, capacity planning, "
            "zero-downtime deployment strategies, chaos engineering basics, and reliability patterns."
        ),
        "price": 16999,
        "discount_price": 12999,
        "category": "AWS",
        "instructor": "Meena R",
        "quizzes_count": 9,
        "students_count": 130,
        "rating": 4.4,
    },
    {
        "slug": "fastapi-backend-engineering",
        "title": "FastAPI Backend Engineering",
        "thumbnail": "/images/python-logo.png",
        "description": (
            "Production-grade API development with FastAPI: async endpoints, Pydantic models, "
            "SQLAlchemy ORM, JWT authentication, RBAC middleware, Razorpay payment integration, "
            "background tasks, file uploads, email services, and Dockerized deployment."
        ),
        "price": 18999,
        "discount_price": 13999,
        "category": "Python",
        "instructor": "Priya N",
        "quizzes_count": 10,
        "students_count": 210,
        "rating": 4.8,
    },
]

INTERVIEW_DOMAINS_SEED = [
    ("Data Structures & Algorithms", "dsa", "#6C63FF", 1),
    ("System Design", "system-design", "#0F6E56", 2),
    ("Python", "python", "#854F0B", 3),
    ("Java", "java", "#185FA5", 4),
    ("SQL", "sql", "#993C1D", 5),
    ("Cloud & DevOps", "cloud", "#993556", 6),
    ("HR & Behavioural", "hr", "#B03A4C", 7),
]

INTERVIEW_QUESTION_SEED = [
    # ── DSA ──────────────────────────────────────────────────────────────
    {
        "title": "Find maximum subarray sum (Kadane's Algorithm)",
        "slug": "maximum-subarray-kadane",
        "domain": "dsa",
        "difficulty": "medium",
        "type": "coding",
        "body": "Given an integer array nums, find the contiguous subarray with the largest sum and return its sum.",
        "hint": "Carry forward the best subarray ending at each index.",
        "answer": "Use Kadane's algorithm: track current_max and global_max. At each element, current_max = max(num, current_max + num). Time: O(n), Space: O(1).",
        "tags": ["arrays", "dynamic-programming", "kadane"],
        "companies": ["Amazon", "Google", "Zoho"],
        "views": 1500,
    },
    # ── System Design ─────────────────────────────────────────────────────
    {
        "title": "Design a URL Shortener (like bit.ly)",
        "slug": "design-url-shortener",
        "domain": "system-design",
        "difficulty": "medium",
        "type": "design",
        "body": "Design a scalable URL shortener with redirect analytics and high availability.",
        "hint": "Cover API, DB, Base62 key generation, and cache strategy.",
        "answer": "Use key generation service + Redis cache for hot URLs + write-optimized DB + async analytics pipeline. Consider consistent hashing for distributed key generation.",
        "tags": ["hld", "hashing", "caching"],
        "companies": ["Amazon", "Freshworks"],
        "views": 820,
    },
    {
        "title": "How do you optimize API performance in a full stack app?",
        "slug": "api-performance-optimization",
        "domain": "system-design",
        "difficulty": "medium",
        "type": "design",
        "body": "Discuss caching, pagination, indexing, compression, and monitoring strategies to optimize a REST API.",
        "hint": "Explain bottleneck isolation and progressive optimization.",
        "answer": "Profile first using APM tools. Add DB indexes, paginate large result sets, use Redis for caching hot data, enable gzip compression, and set up observability dashboards.",
        "tags": ["api", "performance", "backend"],
        "companies": ["Google", "Freshworks"],
        "views": 380,
    },
    # ── Python ────────────────────────────────────────────────────────────
    {
        "title": "What is the difference between list and tuple in Python?",
        "slug": "python-list-vs-tuple",
        "domain": "python",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Explain the differences between Python list and tuple, including mutability, memory usage, and when to use each.",
        "hint": "Mutability, memory, and hashability are the key points.",
        "answer": "Lists are mutable (can be changed), tuples are immutable (fixed after creation). Tuples use less memory and are hashable so they can be used as dictionary keys. Use tuples for fixed data like coordinates, lists for dynamic collections.",
        "tags": ["python-basics", "collections"],
        "companies": ["TCS", "Infosys"],
        "views": 560,
    },
    {
        "title": "What are Python decorators and how do they work?",
        "slug": "python-decorators",
        "domain": "python",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Explain decorators in Python, how they are implemented, and provide a real-world use case.",
        "hint": "Decorators are higher-order functions that wrap other functions.",
        "answer": "A decorator is a function that takes another function and extends its behavior without modifying it. Syntax: @decorator_name. Common uses: logging, authentication, caching, timing. Under the hood: func = decorator(func).",
        "tags": ["python-advanced", "functions"],
        "companies": ["Amazon", "Zoho", "Freshworks"],
        "views": 720,
    },
    {
        "title": "Explain Python generators and when to use them",
        "slug": "python-generators",
        "domain": "python",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "What are generators in Python? How do they differ from regular functions and list comprehensions?",
        "hint": "Think about memory efficiency and lazy evaluation.",
        "answer": "Generators use 'yield' to produce values lazily one at a time, maintaining state between calls. They are memory-efficient for large datasets as they don't store all values in memory. Created with yield keyword or generator expressions ().",
        "tags": ["python-advanced", "memory-management"],
        "companies": ["TCS", "Wipro", "Amazon"],
        "views": 480,
    },
    # ── Java ──────────────────────────────────────────────────────────────
    {
        "title": "How does HashMap work internally in Java?",
        "slug": "java-hashmap-internals",
        "domain": "java",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Explain hashing, buckets, collision resolution, load factor, and rehashing in Java HashMap.",
        "hint": "Mention load factor (0.75), initial capacity (16), and treeification at bucket size 8.",
        "answer": "HashMap uses array of buckets. Each key is hashed to get bucket index. Collisions handled by chaining (LinkedList, treeified to Red-Black tree at size 8). Resizes when size > capacity * load_factor (0.75). Default capacity 16.",
        "tags": ["java", "collections", "hashing"],
        "companies": ["Wipro", "Zoho", "TCS"],
        "views": 690,
    },
    {
        "title": "What is the difference between ArrayList and LinkedList in Java?",
        "slug": "java-arraylist-vs-linkedlist",
        "domain": "java",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Compare ArrayList and LinkedList in Java: underlying structure, performance, and use cases.",
        "hint": "Think about random access vs insertion/deletion performance.",
        "answer": "ArrayList uses dynamic array - O(1) random access, O(n) insertion/deletion in middle. LinkedList uses doubly linked nodes - O(n) access, O(1) insertion/deletion with iterator. Use ArrayList for frequent reads, LinkedList for frequent insertions/deletions.",
        "tags": ["java", "collections", "data-structures"],
        "companies": ["TCS", "Infosys", "Cognizant"],
        "views": 810,
    },
    {
        "title": "What is the difference between abstract class and interface in Java?",
        "slug": "java-abstract-vs-interface",
        "domain": "java",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Explain abstract class vs interface in Java with examples and when to use each (Java 8+).",
        "hint": "Consider state, multiple inheritance, and Java 8 default methods.",
        "answer": "Abstract class: can have state (fields), constructors, concrete methods, single inheritance only. Interface: no state (before Java 8), multiple inheritance, all abstract (Java 8 added default/static methods). Use abstract class for IS-A with shared state, interface for CAN-DO contracts.",
        "tags": ["java", "oop", "design"],
        "companies": ["Wipro", "Amazon", "TCS"],
        "views": 950,
    },
    {
        "title": "What is Spring Boot and how does it differ from Spring MVC?",
        "slug": "spring-boot-vs-spring-mvc",
        "domain": "java",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Explain Spring Boot's auto-configuration, embedded server, and starters vs traditional Spring MVC setup.",
        "hint": "Focus on configuration overhead reduction and embedded Tomcat.",
        "answer": "Spring Boot is an opinionated framework built on top of Spring. It provides auto-configuration, embedded Tomcat/Jetty, starter dependencies, and production-ready features (Actuator). Spring MVC requires manual XML/Java config, WAR deployment. Spring Boot eliminates boilerplate and enables rapid development.",
        "tags": ["java", "spring", "microservices"],
        "companies": ["Infosys", "Wipro", "Freshworks"],
        "views": 1100,
    },
    # ── SQL ────────────────────────────────────────────────────────────────
    {
        "title": "What is the difference between DELETE, TRUNCATE, and DROP?",
        "slug": "sql-delete-truncate-drop",
        "domain": "sql",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Explain the differences between DELETE, TRUNCATE, and DROP in SQL with transaction behavior and use cases.",
        "hint": "Think about DML vs DDL, rollback capability, and WHERE clause support.",
        "answer": "DELETE: DML, removes specific rows, can be rolled back, triggers fire, WHERE supported. TRUNCATE: DDL, removes all rows fast, cannot be rolled back in most DBs, no triggers, resets identity. DROP: DDL, removes entire table structure and data, cannot be rolled back.",
        "tags": ["sql", "dml", "ddl"],
        "companies": ["TCS", "Infosys", "Wipro"],
        "views": 1350,
    },
    {
        "title": "What is the difference between WHERE, GROUP BY, and HAVING?",
        "slug": "sql-where-groupby-having",
        "domain": "sql",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Explain WHERE vs GROUP BY vs HAVING in SQL. When is each clause applied in query execution?",
        "hint": "Consider the order of SQL clause execution.",
        "answer": "WHERE filters rows before grouping (cannot use aggregate functions). GROUP BY groups rows with same values. HAVING filters groups after aggregation (can use aggregate functions like COUNT, SUM). Execution order: FROM -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY.",
        "tags": ["sql", "aggregation", "filtering"],
        "companies": ["TCS", "Cognizant", "Infosys"],
        "views": 1120,
    },
    {
        "title": "Write a SQL query to find the second highest salary",
        "slug": "sql-second-highest-salary",
        "domain": "sql",
        "difficulty": "medium",
        "type": "coding",
        "body": "Given an Employee table with columns (emp_id, name, salary), write a query to return the employee(s) with the second highest salary.",
        "hint": "Use DENSE_RANK window function or a subquery excluding MAX.",
        "answer": "Using window function: SELECT name, salary FROM (SELECT name, salary, DENSE_RANK() OVER (ORDER BY salary DESC) as rnk FROM Employee) t WHERE rnk = 2. Alternative: SELECT MAX(salary) FROM Employee WHERE salary < (SELECT MAX(salary) FROM Employee).",
        "tags": ["sql", "window-functions", "subquery"],
        "companies": ["Infosys", "Cognizant", "TCS"],
        "views": 1100,
    },
    {
        "title": "Explain all types of JOINs with a scenario",
        "slug": "sql-joins-explained",
        "domain": "sql",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Given Table A (1,2,3,5,6) and Table B (3,4,5,6), what will be the result count for INNER JOIN, LEFT JOIN, RIGHT JOIN, and FULL OUTER JOIN? Explain your reasoning.",
        "hint": "Think about which rows from each table are included in each join type.",
        "answer": "INNER JOIN: only matching rows = {3,5,6} = 3 rows. LEFT JOIN: all of A with matching B = {1,2,3,5,6} = 5 rows. RIGHT JOIN: all of B with matching A = {3,4,5,6} = 4 rows. FULL OUTER JOIN: all rows from both = {1,2,3,4,5,6} = 6 rows.",
        "tags": ["sql", "joins", "scenario"],
        "companies": ["TCS", "Wipro", "Infosys", "Amazon"],
        "views": 980,
    },
    {
        "title": "What is PL/SQL and where is it used?",
        "slug": "plsql-usage",
        "domain": "sql",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Explain PL/SQL: what it is, its block structure, and why enterprises use it over plain SQL.",
        "hint": "PL/SQL adds procedural programming to SQL.",
        "answer": "PL/SQL (Procedural Language/SQL) is Oracle's extension that adds procedural programming (loops, conditions, error handling) to SQL. Block structure: DECLARE -> BEGIN -> EXCEPTION -> END. Used for stored procedures, functions, triggers, packages in banking, ERP, telecom. Reduces network round trips and adds business logic at DB layer.",
        "tags": ["oracle", "plsql", "stored-procedures"],
        "companies": ["TCS", "Wipro", "Oracle"],
        "views": 470,
    },
    {
        "title": "Explain SQL constraints and their differences",
        "slug": "sql-constraints",
        "domain": "sql",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "What are SQL constraints? Explain PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL, CHECK, and DEFAULT with differences.",
        "hint": "Think about data integrity enforcement at different levels.",
        "answer": "PRIMARY KEY: unique + not null, only one per table. UNIQUE: unique values allowed, can have NULLs, multiple per table. FOREIGN KEY: references another table's PK for referential integrity. NOT NULL: prevents NULL values. CHECK: validates values against a condition. DEFAULT: sets default value if none provided.",
        "tags": ["sql", "constraints", "data-integrity"],
        "companies": ["TCS", "Infosys", "Cognizant"],
        "views": 760,
    },
    # ── Cloud & DevOps ────────────────────────────────────────────────────
    {
        "title": "What happens in a CI/CD pipeline from commit to production?",
        "slug": "cicd-pipeline-flow",
        "domain": "cloud",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Walk through the complete CI/CD pipeline stages from a developer pushing code to it running in production.",
        "hint": "Cover code commit, build, test, artifact, staging, and production with rollback.",
        "answer": "1.Code commit to Git triggers pipeline. 2.CI: code checkout, compile/build, unit tests, code quality scan. 3.Artifact built and pushed to registry. 4.CD: deploy to staging, run integration/smoke tests. 5.Manual gate or auto-promote to production. 6.Health checks post-deploy; rollback if failed.",
        "tags": ["devops", "cicd", "deployment"],
        "companies": ["Freshworks", "Zoho", "Amazon"],
        "views": 610,
    },
    {
        "title": "What is AWS VPC and how do you design it for a 3-tier web app?",
        "slug": "aws-vpc-web-app",
        "domain": "cloud",
        "difficulty": "hard",
        "type": "design",
        "body": "Design a secure AWS VPC for a 3-tier application with public web layer, private app layer, and database layer across multiple availability zones.",
        "hint": "Think about public/private subnets, NAT gateway, security groups, ALB, and RDS.",
        "answer": "Create VPC with CIDR 10.0.0.0/16. Public subnets for ALB and NAT GW across 2 AZs. Private app subnets for EC2/ECS. Private DB subnets for RDS Multi-AZ. Security Groups: ALB allows 80/443 from internet; app allows 8080 only from ALB SG; DB allows 5432 only from app SG. Internet GW for public, NAT GW for outbound from private.",
        "tags": ["aws", "networking", "vpc", "security"],
        "companies": ["Amazon", "Infosys", "TCS"],
        "views": 530,
    },
    {
        "title": "Explain DevOps principles and the DevOps lifecycle",
        "slug": "devops-principles-lifecycle",
        "domain": "cloud",
        "difficulty": "easy",
        "type": "conceptual",
        "body": "Define DevOps, explain its core principles, and walk through the DevOps lifecycle stages.",
        "hint": "Cover culture, automation, measurement, sharing (CAMS).",
        "answer": "DevOps bridges Dev and Ops teams for faster, reliable delivery. Core principles: Culture (collaboration), Automation (CI/CD, IaC), Measurement (metrics, monitoring), Sharing (feedback loops). Lifecycle: Plan -> Code -> Build -> Test -> Release -> Deploy -> Operate -> Monitor -> back to Plan.",
        "tags": ["devops", "fundamentals", "culture"],
        "companies": ["TCS", "Wipro", "Freshworks"],
        "views": 420,
    },
    {
        "title": "What is the difference between monolithic and microservices architecture?",
        "slug": "monolith-vs-microservices",
        "domain": "cloud",
        "difficulty": "medium",
        "type": "conceptual",
        "body": "Compare monolithic and microservices architectures: structure, deployment, scaling, and fault tolerance.",
        "hint": "Consider team autonomy, independent deployability, and complexity trade-offs.",
        "answer": "Monolith: single deployable unit, simple to develop/test, hard to scale specific parts, single point of failure. Microservices: independently deployable services, each owns its data, scales independently, fault-isolated, but adds network complexity, distributed tracing, and operational overhead.",
        "tags": ["microservices", "architecture", "system-design"],
        "companies": ["Amazon", "Freshworks", "Zoho"],
        "views": 870,
    },
    # ── HR & Behavioural ─────────────────────────────────────────────────
    {
        "title": "Tell me about a time you handled conflict in your team",
        "slug": "hr-team-conflict",
        "domain": "hr",
        "difficulty": "easy",
        "type": "behavioural",
        "body": "Answer this behavioural question using the STAR framework: describe a specific situation where you resolved a conflict within your team.",
        "hint": "Use STAR: Situation, Task, Action, Result. Keep it professional and show collaboration skills.",
        "answer": "Structure with STAR. Example: S-Two team members had disagreement on technical approach, T-needed to deliver feature by deadline, A-facilitated discussion presenting both options with trade-offs, got consensus on hybrid approach, R-feature delivered on time, both team members satisfied. Show communication, empathy, and outcome.",
        "tags": ["star-method", "communication", "teamwork"],
        "companies": ["TCS", "Wipro", "Infosys"],
        "views": 430,
    },
    {
        "title": "Why do you want to work in this company?",
        "slug": "hr-why-this-company",
        "domain": "hr",
        "difficulty": "easy",
        "type": "behavioural",
        "body": "How do you answer 'Why do you want to work here?' effectively in an HR interview?",
        "hint": "Research the company, align with your career goals, and show genuine interest.",
        "answer": "Structure: 1.Show you researched the company (products, culture, values). 2.Connect company strengths to your career goals. 3.Highlight a specific aspect (technology stack, growth opportunities, mission). Avoid: generic answers about salary or proximity. Make it specific and authentic.",
        "tags": ["hr-round", "interview-prep"],
        "companies": ["TCS", "Infosys", "Wipro", "Cognizant"],
        "views": 640,
    },
]

INTERVIEW_TOPICS_SEED = [
    ("dynamic-programming", "Dynamic Programming", "dsa", "DP patterns — memoization, tabulation, knapsack, LCS, and classic problems for coding interviews."),
    ("arrays-strings", "Arrays & Strings", "dsa", "Two-pointer, sliding window, prefix sum, sorting, and pattern problems for coding rounds."),
    ("java-core", "Java Core", "java", "Collections, JVM memory model, OOP principles, exception handling, and concurrency basics."),
    ("spring-boot", "Spring Boot & REST APIs", "java", "Spring Boot auto-configuration, REST controllers, JPA repositories, security, and microservices patterns."),
    ("sql-fundamentals", "SQL Fundamentals", "sql", "SELECT, JOINs, aggregation, subqueries, constraints, and scenario-based query writing."),
    ("plsql-oracle", "PL/SQL & Oracle", "sql", "PL/SQL blocks, stored procedures, cursors, triggers, performance tuning, and enterprise DB patterns."),
    ("aws-core", "AWS Core Services", "cloud", "EC2, S3, RDS, VPC, IAM, Lambda, and CloudWatch — architecture and scenario questions."),
    ("devops-cicd", "DevOps & CI/CD", "cloud", "CI/CD pipelines, Docker, Kubernetes, Infrastructure as Code, and deployment strategies."),
    ("python-basics", "Python Fundamentals", "python", "Data types, collections, functions, OOP, file handling, decorators, and exception management."),
    ("hr-interview", "HR & Behavioural", "hr", "STAR method stories, common HR questions, salary negotiation, and professional communication."),
]


def upsert_seed_courses(db: Session):
    for idx, payload in enumerate(COURSE_SEED):
        row = db.query(Course).filter(Course.slug == payload["slug"]).first()
        lessons_est = 52 + (idx * 3)
        duration_est = lessons_est * 24
        if not row:
            row = Course(
                slug=payload["slug"],
                title=payload["title"],
                thumbnail=payload["thumbnail"],
                description=payload["description"],
                price=payload["price"],
                discount_price=payload["discount_price"],
                category=payload["category"],
                instructor=payload["instructor"],
                lessons_count=lessons_est,
                quizzes_count=payload["quizzes_count"],
                duration_minutes=duration_est,
                students_count=payload["students_count"],
                rating=payload["rating"],
                status="published",
            )
            db.add(row)
            continue

        row.title = payload["title"]
        row.thumbnail = payload["thumbnail"]
        row.description = payload["description"]
        row.price = payload["price"]
        row.discount_price = payload["discount_price"]
        row.category = payload["category"]
        row.instructor = payload["instructor"]
        row.quizzes_count = payload["quizzes_count"]
        row.students_count = payload["students_count"]
        row.rating = payload["rating"]
        row.status = "published"


def upsert_interview_seed(db: Session):
    domain_map = {}
    for name, slug, color_hex, order in INTERVIEW_DOMAINS_SEED:
        row = db.query(InterviewDomain).filter(InterviewDomain.slug == slug).first()
        if not row:
            row = InterviewDomain(name=name, slug=slug, color_hex=color_hex, order=order)
            db.add(row)
            db.flush()
        else:
            row.name = name
            row.color_hex = color_hex
            row.order = order
        domain_map[slug] = row

    for name in ["Google", "Amazon", "TCS", "Infosys", "Wipro", "Zoho", "Freshworks", "Cognizant", "Microsoft"]:
        slug = slugify(name)
        row = db.query(QuestionCompany).filter(QuestionCompany.slug == slug).first()
        if not row:
            db.add(QuestionCompany(name=name, slug=slug))

    db.flush()

    for qd in INTERVIEW_QUESTION_SEED:
        q = db.query(InterviewQuestion).filter(InterviewQuestion.slug == qd["slug"]).first()
        if not q:
            q = InterviewQuestion(slug=qd["slug"])
            db.add(q)
        q.title = qd["title"]
        q.body = qd["body"]
        q.domain_id = domain_map[qd["domain"]].id if qd["domain"] in domain_map else None
        q.difficulty = qd["difficulty"]
        q.type = qd["type"]
        q.hint = qd["hint"]
        q.answer = qd["answer"]
        q.status = "published"
        q.views = qd["views"]
        db.flush()

        db.query(QuestionTagMap).filter(QuestionTagMap.question_id == q.id).delete()
        for t in qd["tags"]:
            ts = slugify(t)
            tag = db.query(QuestionTag).filter(QuestionTag.slug == ts).first()
            if not tag:
                tag = QuestionTag(name=t.replace("-", " ").title(), slug=ts)
                db.add(tag)
                db.flush()
            db.add(QuestionTagMap(question_id=q.id, tag_id=tag.id))

        db.query(QuestionCompanyMap).filter(QuestionCompanyMap.question_id == q.id).delete()
        for cname in qd["companies"]:
            cs = slugify(cname)
            c = db.query(QuestionCompany).filter(QuestionCompany.slug == cs).first()
            if c:
                db.add(QuestionCompanyMap(question_id=q.id, company_id=c.id))

    for slug, name, domain_slug, description in INTERVIEW_TOPICS_SEED:
        t = db.query(InterviewTopic).filter(InterviewTopic.slug == slug).first()
        if not t:
            t = InterviewTopic(slug=slug)
            db.add(t)
        t.name = name
        t.domain_id = domain_map[domain_slug].id if domain_slug in domain_map else None
        t.description = description
        t.cheat_sheet = f"{name} quick revision notes and interviewer expectations."
        t.study_resources_json = [{"label": "Skillfort Resource", "url": "https://course.skillfortinstitute.com"}]
        t.status = "published"


def seed_if_empty(db: Session):
    if db.query(User).count() == 0:
        db.add_all(
            [
                User(full_name="Admin User", email="admin@skillfortinstitute.com", password_hash=hash_password("Skillfort@123"), role="admin"),
                User(full_name="Student User", email="student@skillfortinstitute.com", password_hash=hash_password("Skillfort@123"), role="student"),
                User(full_name="Admin Ops", email="opsadmin@skillfortinstitute.com", password_hash=hash_password("Skillfort@123"), role="admin"),
                User(full_name="Student Demo 2", email="student2@skillfortinstitute.com", password_hash=hash_password("Skillfort@123"), role="student"),
                User(full_name="Instructor Demo", email="instructor@skillfortinstitute.com", password_hash=hash_password("Skillfort@123"), role="instructor"),
            ]
        )
    else:
        for email in [
            "admin@skillfortinstitute.com",
            "opsadmin@skillfortinstitute.com",
            "student@skillfortinstitute.com",
            "student2@skillfortinstitute.com",
            "instructor@skillfortinstitute.com",
        ]:
            u = db.query(User).filter(User.email == email).first()
            if u:
                u.password_hash = hash_password("Skillfort@123")
                u.is_active = True

    upsert_seed_courses(db)
    db.flush()

    if db.query(CourseLesson).count() == 0:
        published_courses = db.query(Course).filter(Course.status == "published").all()
        for c in published_courses:
            db.add_all(
                [
                    CourseLesson(
                        course_id=c.id,
                        section_title="Getting Started",
                        lesson_title="Course Introduction",
                        duration_minutes=18,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        order_index=1,
                        is_preview=True,
                    ),
                    CourseLesson(
                        course_id=c.id,
                        section_title="Core Concepts",
                        lesson_title="Hands-on Implementation",
                        duration_minutes=32,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        order_index=2,
                        is_preview=False,
                    ),
                    CourseLesson(
                        course_id=c.id,
                        section_title="Interview Track",
                        lesson_title="Top Interview Questions Walkthrough",
                        duration_minutes=28,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        order_index=3,
                        is_preview=False,
                    ),
                ]
            )

        for c in published_courses:
            total = db.query(func.coalesce(func.sum(CourseLesson.duration_minutes), 0)).filter(CourseLesson.course_id == c.id).scalar() or 0
            c.duration_minutes = int(total)
            c.lessons_count = db.query(CourseLesson).filter(CourseLesson.course_id == c.id).count()

    if db.query(Category).count() == 0:
        for name in ["Full Stack Training", "Python", "Java", "Oracle", "AWS", "Data Analyst"]:
            db.add(Category(name=name, slug=slugify(name), is_active=True))

    upsert_interview_seed(db)

    if db.query(StudyPlannerTemplate).count() == 0:
        db.add_all(
            [
                StudyPlannerTemplate(name="30 Day Sprint", duration_days=30, description="High-intensity prep plan"),
                StudyPlannerTemplate(name="60 Day Balanced", duration_days=60, description="Balanced prep plan"),
                StudyPlannerTemplate(name="90 Day Deep Mastery", duration_days=90, description="Long-form mastery plan"),
            ]
        )

    if db.query(Coupon).count() == 0:
        db.add_all(
            [
                Coupon(code="SKILLFORT10", discount_percent=10, max_uses=500, used_count=31, is_active=True),
                Coupon(code="PLACEMENT20", discount_percent=20, max_uses=200, used_count=19, is_active=True),
            ]
        )

    default_settings = {
        "site_name": "Skillfort Institute LMS",
        "support_email": "info@skillfortinstitute.com",
        "support_phone": "+91 93449 93939",
        "maintenance_mode": "false",
        "social_facebook": "https://www.facebook.com/skillfortinstitute",
        "social_instagram": "https://www.instagram.com/skillfortinstitute",
        "social_linkedin": "https://www.linkedin.com/company/skillfort-institute",
        "social_x": "https://x.com/skillfortinstitute",
        "about_us_content": "SkillFort Software Training & Placements bridges the gap between education and employment with practical software training, mentorship, and placement-driven outcomes.",
        "terms_conditions_content": "By using Skillfort LMS, you agree to use the platform responsibly and comply with course access policies. Course content is for enrolled learners only.",
        "privacy_policy_content": "Skillfort LMS collects essential account and learning data to provide training services. We do not sell personal data to third parties.",
    }
    for key, value in default_settings.items():
        row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if not row:
            db.add(SiteSetting(key=key, value=value))

    if db.query(Order).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        course = db.query(Course).filter(Course.status == "published").first()
        if student and course:
            o = Order(
                order_id="SF-DEMO-1001",
                razorpay_order_id="demo_order_1001",
                razorpay_payment_id="demo_payment_1001",
                user_id=student.id,
                course_id=course.id,
                amount=course.discount_price * 100,
                status="paid",
            )
            db.add(o)
            db.flush()
            db.add(
                Certificate(
                    user_id=student.id,
                    course_id=course.id,
                    certificate_no="CERT-DEMO-1001",
                    file_path="./storage/certificates/CERT-DEMO-1001.pdf",
                )
            )

    if db.query(Review).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        course = db.query(Course).filter(Course.status == "published").first()
        if student and course:
            db.add(
                Review(
                    user_id=student.id,
                    course_id=course.id,
                    rating=5,
                    comment="Great placement-focused course.",
                    status="approved",
                )
            )

    if db.query(Enrollment).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        courses = db.query(Course).filter(Course.status == "published").limit(4).all()
        if student:
            for idx, c in enumerate(courses):
                db.add(
                    Enrollment(
                        user_id=student.id,
                        course_id=c.id,
                        progress_percent=min(100, idx * 35),
                        completed=idx >= 3,
                        last_lesson=f"Lesson {min(5, c.lessons_count)}",
                    )
                )

    if db.query(StudentProfile).count() == 0:
        students = db.query(User).filter(User.role == "student").all()
        for s in students:
            db.add(StudentProfile(user_id=s.id, phone="", city="Chennai", bio="Skillfort student", photo_url=""))

    if db.query(Notification).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        if student:
            db.add_all(
                [
                    Notification(user_id=student.id, title="Welcome to Skillfort", message="Your learning dashboard is ready.", is_read=False),
                    Notification(user_id=student.id, title="New Mock Interview Set", message="Try the latest DSA mock interview.", is_read=False),
                ]
            )

    if db.query(CourseNote).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        enrollment = db.query(Enrollment).first()
        if student and enrollment:
            db.add(
                CourseNote(
                    user_id=student.id,
                    course_id=enrollment.course_id,
                    lesson_title="Introduction",
                    note_text="Focus on clean architecture and consistent API contracts.",
                )
            )

    if db.query(QuizAttempt).count() == 0:
        student = db.query(User).filter(User.role == "student").first()
        enrollment = db.query(Enrollment).first()
        if student and enrollment:
            db.add(QuizAttempt(user_id=student.id, course_id=enrollment.course_id, score=8, total=10))

    db.commit()
