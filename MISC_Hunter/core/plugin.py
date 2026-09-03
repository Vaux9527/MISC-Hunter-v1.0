'''
各种Plugin的基类
用来全局规定插件的具体实现
'''

class Plugin:

    name = "Base Plugin"
    version = "1.0"

    def run(self, context):
        raise NotImplementedError   #报警：未实现  