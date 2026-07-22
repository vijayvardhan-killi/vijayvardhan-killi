"""
Neofetch-style GitHub profile SVG.
Computes REAL stats by querying the GitHub API and cloning public repos
to sum commits + lines of code, same technique the original uses.

Run inside GitHub Actions where GITHUB_TOKEN is provided automatically.
"""
import os
import re
import json
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime

USERNAME = "vijayvardhan-killi"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": USERNAME}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def fetch_user():
    return get_json(f"https://api.github.com/users/{USERNAME}")


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = get_json(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_contributions_this_year():
    req = urllib.request.Request(
        f"https://github.com/users/{USERNAME}/contributions",
        headers={"User-Agent": USERNAME},
    )
    with urllib.request.urlopen(req) as r:
        html = r.read().decode()
    m = re.search(r'(\d[\d,]*)\s*\n\s*contributions?\s*\n\s*in the last year', html)
    if m:
        return int(m.group(1).replace(",", ""))
    counts = re.findall(r'data-count="(\d+)"', html)
    return sum(int(c) for c in counts)


def clone_and_measure(repos):
    total_commits = 0
    total_add = 0
    total_del = 0
    tmp = tempfile.mkdtemp(prefix="loc_scan_")
    try:
        for repo in repos:
            if repo.get("fork"):
                continue
            name = repo["name"]
            url = repo["clone_url"]
            dest = os.path.join(tmp, name)
            try:
                subprocess.run(
                    ["git", "clone", "--quiet", url, dest],
                    check=True, timeout=120,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                commit_count = subprocess.run(
                    ["git", "-C", dest, "log", "--oneline"],
                    capture_output=True, text=True, timeout=60,
                ).stdout.strip().splitlines()
                total_commits += len(commit_count)

                numstat = subprocess.run(
                    ["git", "-C", dest, "log", "--numstat", "--pretty=tformat:"],
                    capture_output=True, text=True, timeout=60,
                ).stdout
                for line in numstat.splitlines():
                    parts = line.split("\t")
                    if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                        total_add += int(parts[0])
                        total_del += int(parts[1])
            except Exception as e:
                print(f"skip {name}: {e}")
            finally:
                shutil.rmtree(dest, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return total_commits, total_add, total_del


def dots(label_len, value_col=30):
    n = max(1, value_col - label_len)
    return " " + ("." * n) + " "



ASCII_ART_RAW = r"""
⠀⠀⠈⠒⠛⠛⢁⠀⠙⠛⠋⢁⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⣩⠟⣡⡆⠀⠀⢀⣤⢸⣿⣶⡄⢀⠀⠙⠧⢈⣿⠘⣿⡌⣿⡆⢲⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⣴⠟⠁⣾⣿⡇⢀⣴⣿⣿⢸⣿⣿⣿⠘⣿⣷⠘⣿⣿⡇⢻⣇⢹⣿⡘⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣤⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⣡⡾⠋⠀⢸⣿⢋⣴⢸⣿⣿⣿⠈⣿⣿⣿⡆⢻⣿⡇⢻⣿⣷⠸⣿⡈⣿⣇⠁⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⣡⡾⠋⠀⠀⠀⢘⣡⣿⣿⠸⣿⣿⣿⡄⣿⣿⣿⣧⠸⣿⣿⡈⣿⣿⠄⠻⣇⡈⠿⣷⣤⣑⠢⢀⠀⠀⠀⠀⠀⠀
⢀⣠⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠟⣋⣅⡒⠀⠀⠀⠀⠸⣿⣿⣿⠀⣿⣿⣿⡇⢻⣿⡿⠿⠄⠛⣻⣧⣄⠲⣶⣦⣌⠻⢷⣬⡛⠿⣷⣦⣍⡒⠤⣀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⢀⣴⣾⡿⠋⠀⢀⣠⠞⣠⣾⣶⣶⠎⣠⣤⠀⢠⣤⣄⠲⣾⣿⣿⣷⣌⡙⢿⣷⣬⡙⠿⣿⣦⣌⠛⠷⣤⣙⠻⢿⣶⣦⡍⡁
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⡡⠀⢀⣴⣿⣿⠟⠁⢀⣴⠟⣡⣾⣿⣿⡿⢁⣼⣿⠋⣼⣦⠹⣿⣷⣌⠻⢿⣿⣿⣿⣶⣌⠛⢿⣷⣌⡙⠿⣿⣦⣌⡛⠻⠦⠈⠫⠒⠀
⣿⣿⣿⣿⣿⣿⣿⣿⠟⣋⡴⠋⣠⣾⣿⣿⠛⠁⣠⣾⡿⣡⣾⣿⣿⣿⠋⣴⣿⣿⢃⣾⣿⣿⣷⣌⠻⣿⣷⣦⡙⠿⣿⣿⣿⣿⣦⣈⠛⠿⠶⠈⠛⡫⠭⠆⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⡿⢛⣥⠞⠁⣀⠾⠿⣿⠟⣀⣴⣿⡿⢋⣾⣿⣿⣿⡿⢡⣾⣿⣿⢃⣾⣿⣿⣿⣿⣿⠷⠈⠉⢁⡀⠀⠘⠛⢒⡒⢒⣚⣁⣀⢠⣤⢰⣆⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⠟⣫⣶⠟⠁⠀⠀⠉⠙⠓⠀⠈⠙⠛⠋⠴⣿⣿⣿⣿⠏⣰⣿⣿⡿⢁⣾⣿⣿⠿⠛⠉⠀⠈⠀⠸⠧⣤⡤⠜⠂⢸⡇⣿⣿⢈⣿⢸⣿⢸⣿⡄⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣾⠟⠁⠀⠀⠀⢀⠠⠔⢡⣿⣿⢰⡶⣤⣭⡐⠲⠮⠅⠈⠉⠉⠉⠁⣯⠍⠁⠀⣠⣴⣾⠻⡀⣄⡀⠀⠀⠀⠀⠀⠀⠁⣿⣿⠀⡇⢸⡟⣠⢩⠻⡄⠀⠀⠀⠀⠀
⣿⣿⠛⠁⠀⠀⠀⠀⠀⠀⣠⣶⣿⡿⣿⢸⣧⢻⡟⣇⢿⣶⣦⣤⣀⣀⣀⣀⠀⡔⢀⡆⣌⠻⣿⡀⢀⠘⣿⣷⣶⣶⣶⣿⠇⢀⠛⣿⠀⣿⠘⡇⣿⣆⠂⠈⠂⠀⠀⠀⠀
⠋⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⡿⢡⡗⣦⠻⣾⡇⠈⠜⣿⣿⣿⣿⣮⣉⠻⢯⣴⣿⠃⣿⣷⡌⢷⠀⣷⣬⣿⣿⣿⣿⣿⣾⢸⢁⠇⣤⡙⠠⡀⢹⣿⣦⡀⠀⠀⠀⠀⠀
⠀⣤⣶⣶⣶⣶⡄⠀⢰⠿⠛⠉⣠⣿⣷⣿⠳⡀⠹⡆⠄⡘⢿⣿⣿⣿⣿⣷⣦⣌⡻⠄⣿⢹⣿⣆⠃⣿⣿⣿⣿⣿⣿⣿⣿⠘⠈⣴⣿⣷⡄⢻⣦⣿⣿⣿⡿⠖⠀⠀⠀
⠀⣿⣿⣿⣿⣿⡇⠀⠈⢀⣠⣾⣿⣿⡿⠃⢸⡿⢰⣙⠂⠘⠦⣹⣿⣿⣿⣿⣿⣿⣿⡄⢿⡸⢿⣿⣼⣿⣿⣿⣿⣿⣿⣿⠃⢠⣾⣿⣿⠿⠿⣬⣯⣭⡉⠁⠀⠀⠀⠀⠀
⠀⣿⣿⣿⣿⣿⡇⠀⣦⣴⣤⣦⣴⣶⡆⢠⡿⠁⢹⣿⢳⡄⠰⣶⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⣿⣿⣿⣿⡿⠟⢋⣿⡿⠃⢠⣾⡙⠻⠿⡿⠿⠖⠈⠉⠛⠆⠀⠀⠀⠀⠀
⠀⣿⣿⣿⣿⣿⢧⠀⣿⣿⣿⣿⡿⠋⠠⠋⠀⠀⣿⠃⣼⠂⢰⣦⡙⣿⣷⣮⡭⢭⣭⣶⣶⡶⠶⠶⠶⠖⣲⣿⣿⠟⣱⡆⠡⡙⠿⢦⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣤⣤⣭⣉⡻⠿⡾⠀⢿⣽⣿⣿⣦⣴⣶⡇⠀⠘⣁⡄⠇⢀⠀⠿⣿⣮⡛⣿⣿⣷⣶⣦⣔⠲⣿⣿⣿⣿⣿⠟⣡⣾⣿⢰⠁⢳⢰⣶⡄⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣷⣶⣄⡉⠛⠛⠻⠋⠉⠛⡇⠀⣸⡿⠇⠀⠘⠆⠠⢹⣿⣿⣮⠻⣿⣿⣿⣿⣷⣌⢻⣿⡿⢁⣾⣿⣿⡇⠌⣸⠀⣸⣿⡅⠸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣷⡶⠀⢀⣤⣾⡿⠂⠀⠀⢉⣠⠀⡐⠀⢠⠀⠄⢿⣿⣿⣷⣌⠻⣿⣿⣿⡿⠈⠋⣴⣿⣿⣿⣿⠁⢰⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⢁⣴⣿⣿⡿⠁⠀⢀⣾⣿⡿⠀⣇⠀⢈⣠⢸⡌⣿⣿⣿⣿⣷⣬⣭⣭⣤⣴⣿⣿⣿⣿⣿⡏⠀⠘⢿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⠀⠀⢸⣿⣿⣷⡀⣿⡀⠸⣿⡇⣷⡘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢡⠨⡄⠀⠙⣿⣿⡇⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⠀⠀⠀⣸⣿⣿⣿⡇⢹⣇⠀⢿⡇⣿⣷⡘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠘⢰⣧⠀⠀⠈⠛⠇⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣁⠀⠀⠀⠀⣿⣿⣿⣿⣧⢸⣿⡄⠘⣿⣿⣿⣷⡹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠃⢸⣿⡇⠀⠀⢱⠈⢶⣄⡀⠁⠀⠀⠀⠀⠀⠀⠀⠀
⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⣿⣿⣿⣿⣿⠀⣿⣷⠀⠹⣿⣿⣿⣷⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⣸⣿⡇⠀⠀⠀⠃⠸⣿⣿⣷⣦⣤⣀⠀⠀⠀⠀⠀
"""


ASCII_ART = ASCII_ART_RAW.strip("\n").splitlines()


LOGO = [
    "   █   █ █    █ ▄▀▀▄ ▀▄ ▄▀  ",
    "    █ █  █ ▄  █ █▀▀█   █    ",
    "     ▀   ▀  ▀▀  ▀  ▀   ▀    ",
]

def build_svg(s, mode="dark"):
    if mode == "dark":
        bg = "#161b22"
        ascii_color = "#c9d1d9"
        key_color = "#ffa657"
        value_color = "#a5d6ff"
        cc_color = "#616e7f"
        hd_color = "#c9d1d9"
        add_color = "#3fb950"
        del_color = "#f85149"
        footer_color = "#30363d"
    else:
        bg = "#ffffff"
        ascii_color = "#57606a"
        key_color = "#953800"
        value_color = "#0969da"
        cc_color = "#8c959f"
        hd_color = "#1f2328"
        add_color = "#1a7f37"
        del_color = "#cf222e"
        footer_color = "#d0d7de"

    rows = [
        ("header", "vijayvardhan-killi", None),
        ("rule", None, None),
        ("kv", "Status", "Fresh Graduate, open to work"),
        ("kv", "Degree", "B.Tech, Computer Science"),
        ("kv", "Editor", "VS Code"),
        ("blank", None, None),
        ("kv", "Languages.Programming", "Python, Java, JS, C, C++, Rust, Go, Kotlin"),
        ("kv", "Languages.Web", "React, Django, FastAPI, Flask, Express"),
        ("kv", "Looking for", "SDE / Full-Stack roles"),
        ("blank", None, None),
        ("header2", "- Contact -", None),
        ("kv", "Email", "vijayvardhan.killi@gmail.com"),
        ("kv", "LinkedIn", "vijaya-vardhan-killi"),
        ("kv", "GitHub", USERNAME),
        ("blank", None, None),
        ("header2", "- GitHub Stats -", None),
        ("stat1", None, None),
        ("stat2", None, None),
        ("stat3", None, None),
    ]

    # --- layout constants ---
    main_font = 15
    line_h = 20
    ascii_font = 6          # small font so the dense braille art reads as an image
    ascii_line_h = 8        # tight line-height to keep the art compact/undistorted
    ascii_char_w = ascii_font * 0.62

    max_art_chars = max((len(l) for l in ASCII_ART), default=0)
    ascii_block_w = max_art_chars * ascii_char_w
    ascii_block_h = len(ASCII_ART) * ascii_line_h

    left_margin = 20
    x0 = left_margin + ascii_block_w + 60   # info column starts after the art + gutter

    text_rows_height = 40 + len(rows) * line_h + 30
    svg_h = max(text_rows_height, ascii_block_h + 60)
    svg_w = int(x0 + 650)

    p = []
    
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,Menlo,monospace"  '
        f'width="{svg_w}px" height="{svg_h}px" font-size="{main_font}px">'
    )
    p.append(
        f"<style>.key{{fill:{key_color};}} .value{{fill:{value_color};}} .addColor{{fill:{add_color};}} "
        f".delColor{{fill:{del_color};}} .cc{{fill:{cc_color};}} .hd{{fill:{hd_color};font-weight:bold;}} "
        "text,tspan{white-space:pre;}</style>"
    )
    p.append(f'<rect width="{svg_w}px" height="{svg_h}px" fill="{bg}" rx="15"/>')

    # ascii art column — small font, tight leading, so it reads as a dense image
    y = 100
    p.append(
        f'<text x="{left_margin}" y="{y}" fill="{ascii_color}" '
        f'font-size="{ascii_font}px" '
        f'font-family="Segoe UI Symbol, Noto Sans Symbols, Apple Symbols, Consolas, Menlo, monospace">'
    )
    for line in ASCII_ART:
        p.append(f'<tspan x="{left_margin}" y="{y}">{line}</tspan>')
        y += ascii_line_h
    p.append("</text>")

    logo_y = y + 18

    p.append(
        f'<text x="{left_margin}" y="{logo_y}" '
        f'fill="{ascii_color}" '
        f'font-size="15px" '
        f'font-family="Consolas, Menlo, monospace">'
    )

    for line in LOGO:
        p.append(f'<tspan x="{left_margin}" y="{logo_y}">{line}</tspan>')
        logo_y += 20

    p.append("</text>")



    # info column
    y = 34
    p.append(f'<text x="{x0}" y="{y}">')
    for kind, key, val in rows:
        if kind in ("header", "header2"):
            p.append(f'<tspan x="{x0}" y="{y}" class="hd">{key}</tspan>')
        elif kind == "rule":
            p.append(f'<tspan x="{x0}" y="{y}" class="cc">' + "-" * 46 + "</tspan>")
        elif kind == "blank":
            pass
        elif kind == "kv":
            p.append(
                f'<tspan x="{x0}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">{key}</tspan><tspan class="cc">:</tspan>'
                f'<tspan class="cc">{dots(len(key)+1)}</tspan>'
                f'<tspan class="value">{val}</tspan>'
            )
        elif kind == "stat1":
            p.append(
                f'<tspan x="{x0}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">Repos</tspan><tspan class="cc">:</tspan>'
                f'<tspan class="cc">{dots(6)}</tspan><tspan class="value">{s["repos"]}</tspan>'
                f' {{<tspan class="key">Contributed</tspan>: <tspan class="value">{s["contributions"]}</tspan>}}'
                f' | <tspan class="key">Stars</tspan>: <tspan class="value">{s["stars"]}</tspan>'
            )
        elif kind == "stat2":
            p.append(
                f'<tspan x="{x0}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">Commits</tspan><tspan class="cc">:</tspan>'
                f'<tspan class="cc">{dots(8)}</tspan><tspan class="value">{s["commits"]}</tspan>'
                f' | <tspan class="key">Followers</tspan>: <tspan class="value">{s["followers"]}</tspan>'
            )
        elif kind == "stat3":
            p.append(
                f'<tspan x="{x0}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">Lines of Code on GitHub</tspan><tspan class="cc">:</tspan>'
                f'<tspan class="cc">. </tspan><tspan class="value">{s["loc"]}</tspan>'
                f' ( <tspan class="addColor">{s["add"]}++</tspan>, '
                f'<tspan class="delColor">{s["del"]}--</tspan> )'
            )
        y += line_h
    p.append("</text>")
    p.append(
        f'<text x="{svg_w}" y="{svg_h-10}" fill="{footer_color}" font-size="10px" text-anchor="end">'
        f'last updated {datetime.utcnow().strftime("%Y-%m-%d")}</text>'
    )
    p.append("</svg>")
    return "\n".join(p)


def main():
    try:
        user = fetch_user()
        repos = fetch_repos()
        stars = sum(r.get("stargazers_count", 0) for r in repos)
        contributions = fetch_contributions_this_year()
        commits, add, delete = clone_and_measure(repos)
        s = {
            "repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "stars": stars,
            "contributions": contributions,
            "commits": commits,
            "add": f"{add:,}",
            "del": f"{delete:,}",
            "loc": f"{add - delete:,}",
        }
    except Exception as e:
        print("live fetch failed, using placeholder stats:", e)
        s = {
            "repos": 12, "followers": 8, "stars": 5, "contributions": 340,
            "commits": 180, "add": "12,400", "del": "3,100", "loc": "9,300",
        }

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for mode in ("dark", "light"):
        svg = build_svg(s, mode=mode)
        out = os.path.join(repo_root, f"{mode}_mode.svg")
        with open(out, "w") as f:
            f.write(svg)
        print("wrote", out)


# def main():
#     # Dummy values for local testing
#     s = {
#         "repos": 18,
#         "followers": 42,
#         "stars": 137,
#         "contributions": 1268,
#         "commits": 894,
#         "add": "145,382",
#         "del": "38,914",
#         "loc": "106,468",
#     }

#     import os

#     output_dir = os.path.dirname(os.path.abspath(__file__))

#     for mode in ("dark", "light"):
#         svg = build_svg(s, mode)
#         output = os.path.join(output_dir, f"{mode}_mode.svg")

#         with open(output, "w", encoding="utf-8") as f:
#             f.write(svg)

#         print(f"Generated {output}")


if __name__ == "__main__":
    main()