"""Everything the profile visuals say, in one place.

Edit this file, then rebuild:

    pip install fonttools brotli pillow
    python3 scripts/build_assets.py          # regenerates assets/*.svg

To refresh the website screenshots used inside the project cards:

    pip install playwright && python -m playwright install chromium
    python3 scripts/capture_frames.py        # rewrites scripts/frames/*.jpg

Rule for PROJECTS: only list websites that are live and working. Every project
card links straight to the live site, so a dead deployment shows up as a broken
promise on the profile.
"""

NAME = "Aman Jaiman"
HANDLE = "amanjaiman1"
ROLE = "Founder · Product Manager · Frontend Engineer"
STATUS = "STEALTH MODE · BUILDING SINCE APR 2025"

# Typed one after another in the hero, then deleted. Keep each under ~36 characters.
HERO_PHRASES = [
    "owning discovery → design → release",
    "6 websites live in production",
    "2,000+ users on Sort & Visualize",
    "Next.js · TypeScript · Astro · GSAP",
    "turning ideas into working products",
]
HERO_CHIPS = ["INDIA", "B.TECH CSE · LPU ’24", "NCC CADET"]

# Shown as blips on the hero radar. Angles are clockwise from 3 o'clock.
RADAR_BLIPS = [
    ("FRANKCALCULATOR", 21, 0.75),
    ("AEVOURA", 70, 0.79),
    ("SOCIO TOP PAPER", 148, 0.88),
    ("WARLIFE", 198, 0.87),
    ("KODEX", 307, 0.33),
    ("SORT & VISUALIZE", 317, 0.86),
]

LINKS = {
    "portfolio": "https://portfolio-v2-8h87.vercel.app/",
    "linkedin": "https://www.linkedin.com/in/aman-jaiman/",
    "x": "https://x.com/AMANJAIMAN6",
    "leetcode": "https://leetcode.com/u/amanjaiman890/",
    # jsDelivr serves the PDF as application/pdf, so it opens in the browser instead of GitHub's file viewer
    "resume": "https://cdn.jsdelivr.net/gh/amanjaiman1/Resume@main/Aman_Jaiman_Resume_Template.pdf",
}

# The whoami terminal. Each line is ("cmd", text) or ("out", [(text, colour-name), ...]).
TERMINAL_TITLE = "aman@stealth: ~"
TERMINAL = [
    ("cmd", "whoami"),
    ("out", [("Aman Jaiman", "text"), (" — Founder · Product Manager · Frontend Engineer", "muted")]),
    ("cmd", "cat now.md"),
    ("out", [("● ", "green"), ("Building an independent product venture in stealth", "text"), ("  (Apr 2025 → now)", "dim")]),
    ("out", [("  I own the whole loop: ", "muted"), ("discovery → roadmap → UX → engineering → release", "cyan")]),
    ("cmd", "cat before.md"),
    ("out", [("  Frontend Engineer", "text"), (" @ Optus EdTech (2024–25) · ", "muted"), ("Java & DSA mentor", "text"), (" @ CoderHouse", "muted")]),
    ("out", [("  B.Tech CSE", "text"), (", Lovely Professional University (2020–24) · ", "muted"), ("NCC cadet", "text")]),
    ("cmd", "ls ~/live"),
    ("out", [("sortandvisualize.com  ", "cyan"), ("frankcalculator.com  ", "sky"), ("aevoura  ", "violet"),
             ("socio-top-paper  ", "pink"), ("kodex  ", "amber"), ("warlife", "green")]),
]

PIPELINE_TITLE = ("02 / OPERATING LOOP", "How I take a product from idea to live")
# (stage, two caption lines, icon)
PIPELINE = [
    ("DISCOVER", ("user interviews", "market teardowns"), "search"),
    ("DEFINE", ("PRDs & roadmap", "RICE-ranked backlog"), "doc"),
    ("DESIGN", ("Figma flows", "design systems"), "pen"),
    ("BUILD", ("Next.js · Astro", "TypeScript · Tailwind"), "code"),
    ("SHIP", ("Vercel · CI/CD", "SEO & analytics"), "plane"),
]
PIPELINE_LOOP_LABEL = "MEASURE → LEARN → ITERATE"

FIGURES_TITLE = ("03 / BY THE NUMBERS", "Figures I can point to")
# (kicker, value, caption). Digits in the value roll like an odometer.
FIGURES = [
    ("SORT & VISUALIZE", "2,000+", "users in its first 2 months"),
    ("GLOBAL REACH", "50+", "countries using Sort & Visualize"),
    ("SHIPPED", "6", "websites live and working"),
    ("SOCIO TOP PAPER", "17,059", "answer pages made searchable"),
    ("MENTORING", "300+", "students taught Java & DSA"),
    ("PROBLEM SOLVING", "500+", "LeetCode problems solved"),
    ("GOOGLE KICK START", "#1542", "global rank, Round H 2022"),
    ("OPEN SOURCE", "230+", "stars across my GitHub repos"),
]

SHIPPED_TITLE = ("04 / LIVE IN PRODUCTION", "Websites that are up and working today")

# frames: screenshots that scroll inside the card's browser window, captured by
# capture_frames.py. "shot" is the file name in scripts/frames/.
PROJECTS = [
    {
        "key": "sort-and-visualize",
        "title": "Sort & Visualize",
        "url": "https://sortandvisualize.com",
        "badge": "2,000+ USERS",
        "desc": "Watch 10 sorting algorithms run step by step with live pseudocode, counters and sound. "
                "Plus 42 written guides.",
        "chips": ["Astro", "Tailwind v4", "JavaScript", "SEO"],
        "frames": [
            {"shot": "sortviz-1", "domain": "sortandvisualize.com", "url": "https://sortandvisualize.com"},
            {"shot": "sortviz-2", "domain": "sortandvisualize.com/visualiser", "url": "https://sortandvisualize.com/visualiser",
             "click": "Sort", "wait_after": 2600},
            {"shot": "sortviz-3", "domain": "sortandvisualize.com/docs", "url": "https://sortandvisualize.com/docs"},
        ],
    },
    {
        "key": "frankcalculator",
        "title": "FrankCalculator",
        "url": "https://frankcalculator.com",
        "badge": "8 CALCULATORS",
        "desc": "Eight free US financial calculators with charts, PDF reports and 30+ plain-English "
                "guides. No sign-up needed.",
        "chips": ["Next.js", "Chart.js", "jsPDF", "Framer Motion"],
        "frames": [
            {"shot": "frank-1", "domain": "frankcalculator.com", "url": "https://frankcalculator.com"},
            {"shot": "frank-2", "domain": "frankcalculator.com/calculators/compound-interest",
             "url": "https://frankcalculator.com/calculators/compound-interest", "scroll": 330},
            {"shot": "frank-3", "domain": "frankcalculator.com/calculators/debt-payoff",
             "url": "https://frankcalculator.com/calculators/debt-payoff", "scroll": 1110, "wait_after": 2500},
        ],
    },
    {
        "key": "aevoura",
        "title": "Aevoura",
        "url": "https://aevoura.vercel.app",
        "badge": "3 LIVE DEMOS",
        "desc": "A storefront for premium website templates, each with a real live demo: jewellery, "
                "architecture and personal-brand builds.",
        "chips": ["Next.js 16", "React 19", "GSAP", "Lenis"],
        "frames": [
            {"shot": "aevoura-1", "domain": "aevoura.vercel.app", "url": "https://aevoura.vercel.app"},
            {"shot": "aevoura-2", "domain": "temp-jwel.vercel.app", "url": "https://temp-jwel.vercel.app"},
            {"shot": "aevoura-3", "domain": "temp-interior.vercel.app", "url": "https://temp-interior.vercel.app"},
            {"shot": "aevoura-4", "domain": "temp-marketing-eight.vercel.app", "url": "https://temp-marketing-eight.vercel.app"},
        ],
    },
    {
        "key": "socio-top-paper",
        "title": "Socio Top Paper",
        "url": "https://topper-paper-socio.vercel.app",
        "badge": "17,059 PAGES",
        "desc": "Search UPSC Sociology topper answers by question, thinker or topper, then open the "
                "exact page of the original copy.",
        "chips": ["Next.js", "Web Workers", "IndexedDB", "Sheets API"],
        "frames": [
            {"shot": "socio-1", "domain": "topper-paper-socio.vercel.app", "url": "https://topper-paper-socio.vercel.app",
             "wait_after": 6000},
            {"shot": "socio-2", "domain": "topper-paper-socio.vercel.app/?q=weber",
             "url": "https://topper-paper-socio.vercel.app/?q=weber", "wait_after": 6000, "scroll": 330},
        ],
    },
    {
        "key": "kodex",
        "title": "Kodex",
        "url": "https://try-test-eta.vercel.app",
        "badge": "100 LESSONS",
        "desc": "A gamified Java + DSA academy: 100 story-driven lessons with XP, levels, a roadmap, "
                "practice sets and quizzes.",
        "chips": ["Next.js", "TypeScript", "Radix UI", "Framer Motion"],
        "frames": [
            {"shot": "kodex-1", "domain": "try-test-eta.vercel.app", "url": "https://try-test-eta.vercel.app"},
            {"shot": "kodex-2", "domain": "try-test-eta.vercel.app/dashboard", "url": "https://try-test-eta.vercel.app/dashboard"},
            {"shot": "kodex-3", "domain": "try-test-eta.vercel.app/learn/day-1", "url": "https://try-test-eta.vercel.app/learn/day-1"},
        ],
    },
    {
        "key": "warlife",
        "title": "Warlife",
        "url": "https://jesus-2-five.vercel.app",
        "badge": "12 STORIES",
        "desc": "My journal of stories and philosophy: 12 essays across 4 themes, with search, RSS "
                "and spam-filtered comments.",
        "chips": ["Astro", "Tailwind v4", "RSS", "Sitemap"],
        "frames": [
            {"shot": "warlife-1", "domain": "jesus-2-five.vercel.app", "url": "https://jesus-2-five.vercel.app"},
            {"shot": "warlife-2", "domain": "jesus-2-five.vercel.app/blog", "url": "https://jesus-2-five.vercel.app/blog"},
            {"shot": "warlife-3", "domain": "jesus-2-five.vercel.app/blog/relationship-beyond-expectations",
             "url": "https://jesus-2-five.vercel.app/blog/relationship-beyond-expectations"},
        ],
    },
]

STACK_TITLE = ("05 / STACK", "What I ship with")
# Icon files come from scripts/icons (skill-icons, MIT licence).
STACK = [
    ("LANGUAGES", ["TypeScript", "JavaScript", "Java-Dark", "CPP", "Python-Dark", "HTML", "CSS"]),
    ("FRONTEND", ["React-Dark", "NextJS-Dark", "Astro", "TailwindCSS-Dark", "ThreeJS-Dark", "Redux", "Vite-Dark"]),
    ("BACKEND & DATA", ["NodeJS-Dark", "ExpressJS-Dark", "Supabase-Dark", "Prisma", "PostgreSQL-Dark", "Firebase-Dark", "MySQL-Dark"]),
    ("SHIP & DESIGN", ["Git", "Github-Dark", "GithubActions-Dark", "Vercel-Dark", "Figma-Dark", "Linux-Dark", "VSCode-Dark"]),
]

JOURNEY_TITLE = ("06 / JOURNEY", "From LPU to building in stealth")
# (date, title, detail)
JOURNEY = [
    ("2020 – 24", "B.Tech CSE", "Lovely Professional Univ."),
    ("OCT 2022", "Google Kick Start", "Round H · rank 1542"),
    ("MAR 2023", "Product_3D", "3D tee customizer · 90+ stars"),
    ("NOV 2023", "Punjab Hackathon", "5th place overall"),
    ("JAN 2024", "NCC camp honours", "Best in Drill & Shooting"),
    ("APR 2024", "Frontend Engineer", "Optus EdTech"),
    ("JUN 2024", "Java & DSA Mentor", "CoderHouse · 300+ students"),
    ("APR 2025", "Founder, in stealth", "independent product venture"),
    ("JUN 2026", "Sort & Visualize", "2,000+ users in 2 months"),
    ("NOW", "6 sites live", "and the next one loading"),
]

LIVE_TITLE = ("07 / LIVE SIGNAL", "Straight from GitHub, refreshed every day")

FOOTER_LINE = "Building in stealth. Shipping in public."
FOOTER_SUB = "thanks for stopping by · github.com/amanjaiman1"
