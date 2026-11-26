# Contributing

Everything in Aequalyn is developed in the open, in the
[Aequalyn organisation on GitHub](https://github.com/Aequalyn). Each part has its own
repository; [The repositories](/docs/repositories/) says which does what.

## Report a problem

Open an issue on the repository the problem belongs to: the desktop's commands and
Hyprland setup in `aequalyn`, the bar, docks, control center and Store in
`aequalyn-shell`, the installer in `aequalyn-installer`, the live ISO in `aequalyn-iso`.
Say what you did, what you expected and what happened, and when you installed or
last updated.

## Send a change

1. Fork the repository and make your change on a branch.
2. Run its tests where it has them (see [Run the shell from a checkout](/docs/run-the-shell/)
   for the shell, `tests/` in the core).
3. Write commit messages the way the project does:
   [Conventional Commits](https://www.conventionalcommits.org/), one short sentence, such as
   `fix(store): keep installed built-in themes under Built-in`.
4. Open a pull request that says what changed and why.

A change that existing installs need goes with a migration in `aequalyn/migrations/`, so
that [updating](/docs/updating/) carries it to every system.

## Publish to the Market

Plugins, themes, wallpaper packs, cursors, looks and apps live in repositories of their own
and reach every Store through the [Market](/docs/market/). Each kind has its guidelines:
start with [Publish a plugin](/docs/publish-plugin/) or [Publish a theme](/docs/publish-theme/).

## This website

The site's source is [aequalyn-site](https://github.com/Aequalyn/aequalyn-site). These
documentation pages are generated from the repositories' own files, so a fix to a
README is a fix to this page too.
