"""Package only public frontend files and Netlify routing rules for manual upload."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / '.local' / 'small-link-netlify.zip'
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name in ('index.html', 'app.js', 'styles.css', '_redirects', '_headers'):
            archive.write(root / 'backend' / 'static' / name, name)
    print(output)


if __name__ == '__main__':
    main()
