"""Pages that only point to a lemma (an inflected form, an alternative spelling), and how
they find the lemma they merge into.

Pointers are filed under the macronized headword their form_of/alt_of target names. The
target is often a page title instead (iuro for iūrō), so rekey_plain_roots refiles those
under the headword with the same letters; promote_orphans turns pointers whose chain never
reaches a lemma into entries; collect_forms gathers what a lemma takes from its pointers.
"""

from collections import defaultdict

from ..models.header import Header
from ..utils import form_of_root, remove_breves
from .related import merged_page


def root_form(senses, language):
    """Return the lemma this entry only points to, or None if any sense defines it."""
    roots = [form_of_root(sense, language) for sense in senses]
    if not roots or None in roots:
        return None
    return roots[0]


def get_header(json_entry):
    plain_word = json_entry.get("word", "")
    head_template = json_entry.get("head_templates", [{}])
    expansion = head_template[0].get("expansion", "")
    return Header(plain_word, expansion, num_headers=1).head_word


def pointer_forms(json_entry):
    sense = json_entry.get("senses", [{}])[0]
    tags = sense.get("tags", [])
    processed_forms = []
    for form in json_entry.get("forms", []):
        if form.get("tags") == ["canonical"]:
            form["tags"] = tags
        processed_forms.append(form)
    # Many pointer pages (innocentum, CON) list no forms: their headword is the only one
    header = get_header(json_entry)
    if all(form.get("form") != header for form in processed_forms):
        processed_forms.insert(0, {"form": header, "tags": tags})
    return processed_forms


def collect_forms(pointers, head_key, part_of_speech, lemma_pos, promoted):
    """Collect forms of entries that only point at head_key (inflections, comparatives,
    alternative spellings), following chains such as a form of an alternative form.
    Return them with the merged pages that are words of their own (see related)."""
    seen_keys = {head_key}
    addl_forms = []
    merged = []
    stack = [head_key]

    while stack:
        curr_key = stack.pop()
        for alt_pos, alt_header, json_entry in pointers.get(curr_key, []):
            if id(json_entry) in promoted:
                continue
            # Leave a direct pointer to a same-POS homograph lemma if one exists
            if (
                curr_key == head_key
                and alt_pos != part_of_speech
                and alt_pos in lemma_pos[head_key]
            ):
                continue
            addl_forms.extend(pointer_forms(json_entry))
            if page := merged_page(json_entry, alt_header):
                merged.append(page)

            sub_key = remove_breves(alt_header)
            # A form spelled like another lemma (ferō, dative of ferus) leads to that
            # lemma's own pointers (lātum, supine of the verb ferō): not this entry's
            if (
                sub_key in pointers
                and sub_key not in seen_keys
                and not lemma_pos.get(sub_key)
            ):
                seen_keys.add(sub_key)
                stack.append(sub_key)
    return addl_forms, merged


def rekey_plain_roots(pointers, known, letters):
    """File pointers whose target is no headword under the headword with its letters, so
    they merge like any other pointer: the target is often a page title without macrons
    ("alternative form of iuro" for iūrō), sometimes macronized otherwise (acontīzō for
    acontizō). letters (Language.letters) gives a spelling's letters; known maps every
    headword to its parts of speech. When several headwords have those letters (latus,
    lātus), the one with the pointer's part of speech is taken, if one is."""
    by_letters = defaultdict(list)
    for header in known:
        by_letters[letters(header)].append(header)

    for key in [k for k in pointers if k not in known]:
        candidates = by_letters.get(letters(key), [])
        if not candidates:
            continue
        stay = []
        for pointer in pointers.pop(key):
            matches = candidates
            if len(matches) > 1:
                matches = [h for h in candidates if pointer[0] in known[h]]
            if len(matches) == 1:
                pointers[matches[0]].append(pointer)
            else:
                stay.append(pointer)
        if stay:
            pointers[key] = stay


def promote_orphans(pointers, lemma_pos):
    """Return pointer entries whose chain never reaches a lemma, so they become entries
    themselves instead of being dropped. Promoted entries can in turn act as roots."""
    reached = set()

    def reach(key):
        stack = [key]
        while stack:
            for _pos, alt_header, obj in pointers.get(stack.pop(), []):
                if id(obj) not in reached:
                    reached.add(id(obj))
                    stack.append(remove_breves(alt_header))

    for key in list(lemma_pos):
        reach(key)

    # Promote the top of each chain first, so the forms that point at an orphan
    # (acontizante at acontizāns) merge into it instead of becoming orphans too
    pointer_keys = {
        remove_breves(alt_header)
        for chain in pointers.values()
        for _pos, alt_header, _obj in chain
    }
    orphans = []
    for tops_only in (True, False):  # the second pass catches cycles
        for key in sorted(pointers):
            if tops_only and key in pointer_keys:
                continue
            for alt_pos, alt_header, obj in pointers[key]:
                if id(obj) in reached:
                    continue
                lemma_pos[remove_breves(alt_header)].add(alt_pos)
                orphans.append((alt_header, alt_pos, obj))
                reached.add(id(obj))
                reach(remove_breves(alt_header))
    return orphans
