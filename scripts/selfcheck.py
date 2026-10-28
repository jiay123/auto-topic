import datetime
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(BASE, "logs")
PY = sys.executable
TODAY = datetime.date.today()

NEWS_STATE = ["state_news_dedup.json"]
TOPICS_STATE = ["state_github_projects.json", "hot_rotation.json", "recommended_history.json"]


def touched_today(names):
    for n in names:
        p = os.path.join(BASE, n)
        if os.path.exists(p):
            if datetime.date.fromtimestamp(os.path.getmtime(p)) == TODAY:
                return True, n
    return False, "-"


def run(script, tag):
    logp = os.path.join(LOGS, tag + ".log")
    with open(logp, "a", encoding="utf-8") as f:
        f.write("\n=== SELFCHECK RETRY %s ===\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        f.flush()
        r = subprocess.run(
            [PY, os.path.join("scripts", script)],
            cwd=BASE, stdout=f, stderr=subprocess.STDOUT,
        )
        f.write("EXIT=%s\n" % r.returncode)


def main():
    os.makedirs(LOGS, exist_ok=True)
    outp = os.path.join(LOGS, "selfcheck.log")
    lines = ["=== SELFCHECK %s ===" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    news_ok, news_file = touched_today(NEWS_STATE)
    topics_ok, topics_file = touched_today(TOPICS_STATE)
    lines.append("news_ok=%s (%s)" % (news_ok, news_file))
    lines.append("topics_ok=%s (%s)" % (topics_ok, topics_file))
    if not news_ok:
        lines.append("ACTION: retry news")
        run("fetch_ai_news.py", "news")
    if not topics_ok:
        lines.append("ACTION: retry topics")
        run("fetch_github_projects.py", "topics")
    if news_ok and topics_ok:
        lines.append("ACTION: none needed")
    with open(outp, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
