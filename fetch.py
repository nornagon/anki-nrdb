"""
Create an [Anki][1] deck from [NetrunnerDB][2]'s card database to help you
remember all the Netrunner cards.

I recommend suspending all cards but the core set (search for `pack:core2`),
and then unsuspending one or two packs at a time.

[1]: https://ankiweb.net/
[2]: https://netrunnerdb.com/
"""
import argparse
import genanki
import json
import os
import requests
import shutil
import sys
import tempfile


MODEL_ID = 2140597657
DECK_ID = 1711046126


class NrdbNote(genanki.Note):
  @property
  def guid(self):
    return genanki.guid_for(self.fields[0])


def main(args):
  r = requests.get('https://netrunnerdb.com/api/2.0/public/cards')
  cards = r.json()

  nrdb_model = genanki.Model(
    MODEL_ID,
    'NetrunnerDB',
    fields=[
      {'name': 'Code'},
      {'name': 'Sequence No.'},
      {'name': 'Title'},
      {'name': 'Text'},
      {'name': 'Type'},
      {'name': 'Side'},
      {'name': 'Faction'},
      {'name': 'Flavor'},
      {'name': 'Pack'},
      {'name': 'Image'},
    ],
    templates=[
      {
        'name': 'Netrunner Card',
        'qfmt': '{{Title}}',
        'afmt': '{{FrontSide}}<hr id="answer">{{Image}}',
      }
    ]
  )

  nrdb_deck = genanki.Deck(
    DECK_ID,
    'NetrunnerDB'
  )

  package = genanki.Package(nrdb_deck)

  for card in cards['data']:
    if card['pack_code'] in args.exclude_pack:
      continue
    img_path = 'images/' + card['code'] + '.png'
    if not os.path.exists(img_path):
      os.makedirs(os.path.dirname(img_path), exist_ok=True)
      url = card.get('image_url', cards['imageUrlTemplate'].format(**card))
      print("Downloading [{}] {}...".format(card['code'], card['title']))
      r = requests.get(url, stream=True)
      try:
        r.raise_for_status()
        with tempfile.NamedTemporaryFile() as img_tmp:
          shutil.copyfileobj(r.raw, img_tmp)
          os.link(img_tmp.name, img_path)
      except requests.exceptions.HTTPError:
        img_path = None
    if img_path:
      package.media_files.append(os.path.basename(img_path))
    note = genanki.Note(
      model=nrdb_model,
      fields=[
        card['code'],
        str(card['position']),
        card['title'],
        card.get('text', ''),
        card['type_code'],
        card['side_code'],
        card['faction_code'],
        card.get('flavor', ''),
        card['pack_code'],
        '<img src="{}">'.format(os.path.basename(img_path)) if img_path else '',
      ]
    )
    nrdb_deck.add_note(note)

  # Anki apparently doesn't like images to be in subdirectories, so...
  os.chdir('images')
  package.write_to_file('../netrunnerdb.apkg')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
      description='Build an Anki deck from NetrunnerDB')
  parser.add_argument('-x', '--exclude-pack', nargs='*', default=[],
      help="Don't make cards with these pack codes. e.g. -x ka rar win")
  main(parser.parse_args(sys.argv[1:]))
