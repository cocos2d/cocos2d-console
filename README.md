# cocos2d-console



## Download

```sh
$ NOT DONE YET
```

## Install

```sh
$ NOT DONE YET
```

## Vision of cocos2d-console


A command line tool that lets you create, run, publish, debug, etc… your game. It is the swiss-army knife for cocos2d.

This command line tool is in its early stages.

Examples:

```
# starts a new project called "My Game" for multi-platform

$ cocos2d new "My Game" -l cpp -p org.cocos2d.mygame

$ cd "My Game"

# Will compile the current project to binrary
$ cocos compile android -m debug


# Will deploy the project to device and run it
$ cocos run android


```

# Devel Info

## Internals

`cocos.py` is an script whose only responsability is to call its plugins.

eg:
```
// It will just print all the registered plugins
$ python cocos.py
```

```
// It will call the "new" plugin
$ python cocos.py project new
``` 

## Adding new plugin to the console

You have to edit the `cocos2d.ini` file, and add your new plugin there.

The plugin accroding it's function divided by category, eg. project, engine ...

Let's say that you want to add a plugin that deploy project.


```
# Adds the deploy plugin
[plugin]
project_deploy.CCPluginDeploy

# should be a subclass of CCPlugin
class = project_deploy.CCPluginDeploy
``` 

And now you have to create a file called `project_delopy.py` with the following structure and put it into `plugins` folder.

```python
import cocos2d

# Plugins should be a sublass of CCPlugin
class CCPluginDeploy(cocos2d.CCPlugin):

        @staticmethod
        def plugin_category():
          return "project"

        @staticmethod
        def plugin_name():
          return "deoply"

        @staticmethod
        def brief_description():
            return "Deploy the project to target."                

        def run(self, argv):
            print "plugin called!"
            print argv

```
