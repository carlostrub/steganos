import re


def get_all_branchpoints(text):
    # local and unicode branchpoints are sorted to maximize the information
    # that can be retrieved from any contiguous piece of encoded text
    sorted_branchpoints = sort_branchpoints(ascii_branchpoints(text) +
                                            unicode_branchpoints(text))
    branchpoints = global_branchpoints(text) + sorted_branchpoints

    unchangeable_areas = find_unchangeable_areas(text)
    changeable_branchpoints = [changeable_part(bp, unchangeable_areas)
                               for bp in branchpoints]
    filtered_branchpoints = [bp for bp in changeable_branchpoints if bp]

    nored_branchpoints = remove_redundant_characters(text,
                                                     filtered_branchpoints)
    return mutually_exclusive_branchpoints(nored_branchpoints)


def changeable_part(branchpoint, unchangeable_areas):
    for start, end in unchangeable_areas:
        for change in branchpoint:
            if ((change[0] > start and change[0] < end) or
                    (change[1] > start and change[1] < end) or
                    (change[0] < start and change[1] > end)):
                branchpoint = [c for c in branchpoint if c != change]
    return branchpoint


def find_unchangeable_areas(text):
    url_re = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|'
                        '(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    code_re = re.compile('```.+?```', re.DOTALL)
    markdown_re = re.compile('[!]?\[[^\]]+?\]\([^)]+?\)', re.MULTILINE)

    url = [m.span() for m in url_re.finditer(text)]
    code_markdown = [m.span() for m in code_re.finditer(text)]
    markdown_links = [m.span() for m in markdown_re.finditer(text)]

    return code_markdown + url + markdown_links


def ascii_branchpoints(text):
    return get_tab_branchpoints(text) + get_contraction_branchpoints(text)


def unicode_branchpoints(text):
    return (get_directional_mark_branchpoints(text) +
            get_non_breaking_branchpoints(text) +
            get_zero_width_space_branchpoints(text))


def global_branchpoints(text):
    global_branchpoints = [get_single_quotes_branchpoint(text),
                           get_single_digit_branchpoint(text)]
    return [bp for bp in global_branchpoints if bp]


def get_tab_branchpoints(text):
    tab_indices = [m.start() for m in re.finditer('\t', text)]
    return [[(tab_index, tab_index + 1, '    ')] for tab_index in tab_indices]


def get_contraction_branchpoints(text):
    contractions = [
        ("won't", "will not"),
        ("can't", "cannot"),
        ("isn't", "is not"),
        ("doesn't", "does not"),
        ("would've", "would have"),
        ("how'll", "how will"),
        ("hadn't", "had not"),
    ]
    branchpoints = []
    for contraction, long_form in contractions:
        for match in re.finditer(contraction, text):
            start, end = match.span()
            branchpoints.append([(start, end, long_form)])
        for match in re.finditer(long_form, text):
            start, end = match.span()
            branchpoints.append([(start, end, contraction)])
    return branchpoints


def get_single_quotes_branchpoint(text):
    double_quote_indices = [m.start() for m in re.finditer('"', text)]
    return [(index, index + 1, "'") for index in double_quote_indices]


def get_single_digit_branchpoint(text):
    digit_re = re.compile('(?<![\d\.])[1-9](?![\d\.])')
    numbers = {
            '9': 'nine',
            '8': 'eight',
            '7': 'seven',
            '6': 'six',
            '5': 'five',
            '4': 'four',
            '3': 'three',
            '2': 'two',
            '1': 'one'
    }
    single_digit_indices = [m.start() for m in digit_re.finditer(text)]
    return [(index, index + 1, numbers[text[index]])
            for index in single_digit_indices]


def get_directional_mark_branchpoints(text):
    period_indices = [index for index, char in enumerate(text[:-1])
                      if char == '.' and text[index+1].isspace()]
    return [[(index, index, '\u200f\u200e')] for index in period_indices]


def get_non_breaking_branchpoints(text):
    capital_letter_indices = [index for index, char in enumerate(text)
                              if char.isupper()]
    return [[(index + 1, index + 1, '\u2060')]
            for index in capital_letter_indices]


def get_zero_width_space_branchpoints(text):
    word_beginnings = [index for index, char in enumerate(text[:-1])
                       if char.isalpha() and text[index+1].isspace()]
    return [[(index+1, index+1, '\u200b')]
            for index in word_beginnings]


def remove_redundant_characters(original_text, branchpoints):
    """
    This function removes redundant characters for all changes in a list of
    branchpoints.  It shortens changes so that only the necessary characters
    are included and no characters are repeated between the text in the change
    and the original text.

    The purpose of this function is to avoid edge-cases that throw off the
    get_indices_of_encoded_text function.  That function can get confused
    especially when the change string starts with the same character as the
    text it is meant to exchange.

    Examples:

    For the text
    A branchpoint like: [(11, 13, 'she')] would be changed to [(11, 11, 's')]

    For the text: "Therefore they are."
    A branchpoint like: [(0, 9, 'There')] would be changed to [(5, 9, '')]
    """
    return [[remove_redundant_characters_from_change(original_text, change)
            for change in branchpoint]
            for branchpoint in branchpoints]


def remove_redundant_characters_from_change(original_text, change):
    start, end, change_string = change

    for index in range(len(change_string), 0, -1):
        text_to_be_changed = original_text[start:end]
        if (text_to_be_changed and change_string and
                text_to_be_changed[:index] == change_string[:index]):
            start += index
            change_string = change_string[index:]
            break

    for index in range(len(change_string), 0, -1):
        text_to_be_changed = original_text[start:end]
        if (text_to_be_changed and change_string and
                text_to_be_changed[-1 * index:] == change_string[-1 * index:]):
            end -= index
            change_string = change_string[:-1 * index]
            break

    return (start, end, change_string)


def sort_branchpoints(branchpoints):
    """ sorts the branchpoints by the start of the first change"""
    for bp in branchpoints:
        bp.sort()

    def first_change(branchpoint):
        return branchpoint[0][0]

    branchpoints.sort(key=first_change)

    return branchpoints


def branchpoint_area(items):
    return len(items) * sum(i[1] - i[0] for i in items)


def mutually_exclusive_branchpoints(data):
    """
    Data is list of lists of intervals. We'd like to keep the most number of
    high level lists such that none of the intervals intersect.

    This is an approximate, greedy, solution that guarantees no intersection
    but may not be the optimal solution.  It runs at O(n logn) so that's not
    bad.
    """
    data_expanded = [(*d, branchpoint_area(items), i)
                     for i, items in enumerate(data)
                     for d in items]
    data_expanded.sort(key=lambda item: item[0])
    to_remove = set()
    i = 0
    de = data_expanded
    while i < len(de) - 1:
        # make sure current element is not marked for deletion
        if de[i][4] not in to_remove:
            # now we make sure the next item to compare against isn't marked
            # for deletion
            j = i + 1
            try:
                while de[j][4] in to_remove:
                    j += 1
            except IndexError:
                break
            # check if this endpoint is after the next items start
            if de[i][1] >= de[j][0]:
                this_area = de[i][3]
                next_area = de[j][3]
                # pick the item with the least "area" in terms of the higher
                # order list of intervals. This is a heuristic to remove long
                # lists of small intervals. We want those out because they have
                # a higher probability of intersecting with many other lists of
                # intervals.
                if this_area < next_area:
                    to_remove.add(de[j][4])
                else:
                    to_remove.add(de[i][4])
                i -= 1
        i += 1
    return [d for i, d in enumerate(data) if i not in to_remove]
