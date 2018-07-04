# -*- coding: utf-8 -*-
"""
Display numbers of updates for various linux distributions.

Configuration parameters:
    cache_timeout: refresh interval for this module (default 600)
    format: display format for this module, otherwise auto (default None)
    thresholds: specify color thresholds to use
        *(default [(0, 'darkgray'), (10, 'good'),
        (20, 'degraded'), (30, 'orange'), (40, 'bad')])*

Format placeholders:
    {apk}    number of updates, eg 0 .. Alpine     .. NOT TESTED
    {apt}    number of updates, eg 0 .. Debian     .. TESTED
    {cower}  number of updates, eg 0 .. Arch Linux .. TESTED
    {dnf}    number of updates, eg 0 .. Fedora     .. WONT SUPPORT :-)
    {eopkg}  number of updates, eg 0 .. Solus      .. TESTED
    {pacman} number of updates, eg 0 .. Arch Linux .. TESTED
    {pkg}    number of updates, eg 0 .. FreeBSD    .. NOT IMPLEMENTED
    {xbps}   number of updates, eg 0 .. Void Linux .. NOT TESTED
    {yay}    number of updates, eg 0 .. Arch Linux .. TESTED
    {zypper} number of updates, eg 0 .. openSUSE   .. NOT TESTED

Color thresholds:
    xxx: print a color based on the value of `xxx` placeholder

@author lasers

Examples:
```
# custom format
updates {
    format = 'UPD [\?color=pacman {pacman}]/[\?color=cower {cower}]'
}
```

SAMPLE OUTPUT
[{'full_text': 'Apk '}, {'full_text': '3', 'color': '#a9a9a9'}]

14pkgs
[{'full_text': 'Apt '}, {'full_text': '14', 'color': '#00FF00'}]

29and5pkgs
[{'full_text': 'Pacman '}, {'full_text': '29 ', 'color': '#FFFF00'},
{'full_text': 'Cower '}, {'full_text': '5', 'color': '#a9a9a9'}]

35pkgs
[{'full_text': 'Zypper '}, {'full_text': '34', 'color': '#ffa500'}]

45pkgs
[{'full_text': 'Xbps '}, {'full_text': '45', 'color': '#FF0000'}]

no_updates
{'full_text': 'No Updates'}
"""


class Update:
    def __init__(self, parent, name, command):
        self.parent = parent
        self.name = name
        self.command = command

    def get_command_output(self):
        try:
            return self.parent.py3.command_output(self.command)
        except self.parent.py3.CommandError:
            return ''

    def get_updates(self):
        return {self.name: self.count_updates()}

    def count_updates(self):
        return len(self.get_command_output().splitlines())


class Apt(Update):
    def count_updates(self):
        return len(self.get_command_output().splitlines()[1:])


class Apk(Update):
    def count_updates(self):
        return len(self.get_command_output().splitlines()[1:])


class Cower(Update):
    def get_command_output(self):
        try:
            self.parent.py3.command_output(self.command)
            return ''
        except self.parent.py3.CommandError as ce:
            return ce.output


class Eopkg(Update):
    def get_command_output(self):
        output = self.parent.py3.command_output(self.command)
        if "No packages to upgrade." in output:
            return ''
        return output


class Zypper(Update):
    def count_updates(self):
        lines = self.get_command_output().splitlines()
        return len([x for x in lines if x][4:])


class Py3status:
    """
    """

    # available configuration parameters
    cache_timeout = 600
    format = None
    thresholds = [(0, 'darkgray'), (10, 'good'), (20, 'degraded'),
                  (30, 'orange'), (40, 'bad')]

    class Meta:
        deprecated = {
            "rename_placeholder": [
                {
                    "placeholder": "aur",
                    "new": "cower",
                    "format_strings": ["format"],
                }
            ]
        }

    def post_config_hook(self):
        binaries = []
        managers = [
            ("pacman", ["checkupdates"]),
            ("cower", ["cower", "-u"]),
            ("yay", ["yay", "--query", "--upgrades", "--aur"]),
            ("apk", ["apk", "version", "-l", '"<"']),
            ("apt", ["apt", "list", "--upgradeable"]),
            ("eopkg", ["eopkg", "list-upgrades"]),
            ("pkg", ["pkg", "upgrade", "--dry-run", "--quiet"]),
            ("xbps", ["xbps-install", "--update", "--dry-run"]),
            ("zypper", ["zypper", "list-updates"]),
        ]
        if not self.format:
            for name, command in managers:
                if self.py3.check_commands(command[0]):
                    binaries.append(name)
            auto = "[\?not_zero {name} [\?color={binary} {{{binary}}}]]"
            self.format = "[{}|\?show No Updates]".format("[\?soft  ]".join(
                auto.format(binary=x, name=x.capitalize()) for x in binaries
            ))

        self.backends = []
        placeholders = self.py3.get_placeholders_list(self.format)
        for name, command in managers:
            if name in placeholders:
                if name in binaries or self.py3.check_commands(command[0]):
                    try:
                        backend = globals()[name.capitalize()]
                    except KeyError:
                        backend = Update
                    self.backends.append(backend(self, name, command))

        self.thresholds_init = self.py3.get_color_names_list(self.format)

    def updates(self):
        update_data = {}
        for backend in self.backends:
            update_data.update(backend.get_updates())

        for x in self.thresholds_init:
            if x in update_data:
                self.py3.threshold_get_color(update_data[x], x)

        return {
            "cached_until": self.py3.time_in(self.cache_timeout),
            "full_text": self.py3.safe_format(self.format, update_data),
        }


if __name__ == "__main__":
    """
    Run module in test mode.
    """
    from py3status.module_test import module_test

    module_test(Py3status)
