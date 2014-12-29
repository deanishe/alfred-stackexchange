
# StackOverflow Search for Alfred 2 #

Search for answers on StackOverflow.com from Alfred.

## Usage ##

- `.so <query>` — Search StackOverflow.com for `<query>`.
    See below for syntax.
    - `↩` or ` ⌘+NUM` — Open result in default browser
    - `⌘+L` — Show full question title in Alfred's Large Text window

## Query syntax ##

By default, words in `<query>` will be search for in the title of posts. To
specify a tag, prefix it with `.`, e.g. `python` will search for `python` in
the post title, `.python` will search for the tag `python`.

## Results ##

Answered questions will be shown first in the list of results (and have a
tick on their icon).
