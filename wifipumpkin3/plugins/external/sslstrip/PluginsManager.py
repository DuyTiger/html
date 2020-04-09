import inspect

# This file is part of the wifipumpkin3 Open Source Project.
# wifipumpkin3 is licensed under the Apache 2.0.

# Copyright 2020 P0cL4bs Team - Marcos Bomfim (mh4x0f)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class PluginsManager:

    _plugins = {}
    _instance = None

    @property
    def plugins(self):
        return self._plugins

    @plugins.setter
    def plugins(self, p):
        self._plugins[p.getName()] = p()

    def addPlugin(self, p):
        self.plugins = p

    @staticmethod
    def getInstance():
        if PluginsManager._instance == None:
            PluginsManager._instance = PluginsManager()
        return PluginsManager._instance

    def hook(self, plugin, attr, request, *args):
        return getattr(self.plugins[plugin], attr['function'])(request, *args)
        