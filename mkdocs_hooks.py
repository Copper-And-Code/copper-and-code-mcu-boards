# SPDX-License-Identifier: MIT
# MkDocs hooks for the site (mkdocs.yml): pages kept next to their code, outside docs/, go into the
# site too, and relative links work on both GitHub and the site. A link to a page of the site stays
# relative; a link to anything else (a .py file, a folder, a log) points to it on GitHub.
import os
import posixpath
import re

from mkdocs.structure.files import File

REPO = "https://github.com/Copper-And-Code/copper-and-code-mcu-boards"
# repository path -> path in the site
EXTRA = {
    "boards/rp2/WAVESHARE_RP2350_TOUCH_LCD_4/README.md": "boards/rp2350-touch-lcd-4.md",
    "examples/README.md": "examples.md",
    "hardware/rp2350-touch-lcd4-box/README.md": "hardware/rp2350-touch-lcd4-box.md",
}
LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def _root(config):
    return os.path.dirname(os.path.abspath(config.config_file_path))


def on_files(files, config):
    root = _root(config)
    for source, target in EXTRA.items():
        files.append(File.generated(config, target, abs_src_path=os.path.join(root, source)))
    return files


def on_page_markdown(markdown, page, config, files):
    docs = os.path.relpath(config.docs_dir, _root(config)).replace(os.sep, "/")
    from_site = {v: k for k, v in EXTRA.items()}
    here = page.file.src_uri
    repo_here = from_site.get(here, posixpath.join(docs, here))

    def on_site(site_path):
        f = files.get_file_from_path(site_path)
        return f is not None and not f.inclusion.is_excluded()

    def fix(m):
        url = m.group(2)
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", url):
            return m.group(0)
        target, hash_, fragment = url.partition("#")
        repo_target = posixpath.normpath(posixpath.join(posixpath.dirname(repo_here), target))
        if repo_target in EXTRA:
            site_target = EXTRA[repo_target]
        elif repo_target.startswith(docs + "/") and on_site(repo_target[len(docs) + 1 :]):
            site_target = repo_target[len(docs) + 1 :]
        else:
            kind = "tree" if target.endswith("/") or "." not in posixpath.basename(repo_target) else "blob"
            return "%s%s/%s/main/%s%s%s%s" % (m.group(1), REPO, kind, repo_target, hash_, fragment, m.group(3))
        relative = posixpath.relpath(site_target, posixpath.dirname(here) or ".")
        return m.group(1) + relative + hash_ + fragment + m.group(3)

    return LINK.sub(fix, markdown)
