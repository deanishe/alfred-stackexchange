
StackExchange Search for Alfred
===============================

Search for answers on StackExchange sites from [Alfred 4+][alfred].

![](demo.gif "")

<!-- MarkdownTOC autolink="true" autoanchor="true" -->

- [Download](#download)
- [Usage](#usage)
- [Query syntax](#query-syntax)
- [Results](#results)
- [Adding custom searches](#adding-custom-searches)
- [Licensing, thanks](#licensing-thanks)

<!-- /MarkdownTOC -->


<a id="download"></a>
Download
--------

Get StackExchange for Alfred from [GitHub releases][gh-releases].


<a id="usage"></a>
Usage
-----

The main action (keyword `stack`) shows a list of all StackExchange
sites. Choose one to search it.

There is also a search for StackOverflow.com configured (keyword
`.so`), but it is easy to add searches for your own favourite
StackExchange sites.

- `stack [<query>]` — Choose a StackExchange site to search.
    - `↩` — Select site
    - `⌘↩` — Set as default site
    - `⌥↩` — Reveal site icon in Finder
    - `⌘C` — Copy site ID to clipboard (for adding Script Filters)
- `.so <query>` — Search StackOverflow.com for `<query>`.
    See below for syntax.
    - `↩` or ` ⌘+NUM` — Open result in default browser
    - `⌘L` — Show full question title in Alfred's Large Text window


<a id="query-syntax"></a>
Query syntax
------------

Prefix a word in your `<query>` with `.` (full stop) to indicate that
it's a tag, e.g `requests .python` will search for answers tagged
`python` with the query `requests`.


<a id="results"></a>
Results
-------

Answered questions will be shown first in the list of results (and have
a green check mark on their icon).


<a id="adding-custom-searches"></a>
Adding custom searches
----------------------

You can easily add your own searches for specific sites by adding your
own Script Filter with the following Script:

```bash
/usr/bin/python so.py search --site <siteid> "$1"
```

The easiest way to do this is to make and edit a copy of the built-in
StackOverflow.com search.

To get a site ID, use the site search (keyword `stack`) and hit `⌘C` on
the desired site to copy its ID to the clipboard.

You can also use `⌥↩` on a site to reveal its icon in Finder.


<a id="licensing-thanks"></a>
Licensing, thanks
-----------------

This workflow is released under the [MIT Licence][mit].

It is heavily based on [Alfred-Workflow][alfred-workflow], also
[MIT-licensed][mit].


[alfred]: https://www.alfredapp.com/
[mit]: http://opensource.org/licenses/MIT
[alfred-workflow]: http://www.deanishe.net/alfred-workflow/
[gh-releases]: https://github.com/deanishe/alfred-stackoverflow/releases
[demo]: https://raw.githubusercontent.com/deanishe/alfred-stackoverflow/master/demo.gif
