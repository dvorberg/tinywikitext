from tinywikitext.to_html import to_html

def main():
    with open("every_markup.mwiki") as fp:
        wikitext = fp.read()

    print('<!DOCTYPE html>')
    print('<html>',
          '<head>',
          '<meta charset="utf-8">',
          '</head>',
          '<body>',
          sep="\n")
    print(to_html(wikitext()))
    print('</body>', '</html>', sep="\n")


main()
