# Package使用说明

package是pmr的管理对象。一个完整的package在放到pmr服务器上后，用户即可通过pmr命令行指令查找、下载和安装此package到本机上。安装完成的package，可以在用户需要时通过命令行添加到用户的工程中，扩展用户工程的功能模块。

### Package的安装使用

以gaf这个package为例，在cocos的环境配置好了以后，即可用以下命令进行操作。

安装：

```sh
cocos package install gaf
```
安装成功后，进入用户的工程目录，用以下命令将package加入用户工程：

```sh
cocos framework add gaf
```
如果运行一切正常，gaf模块的功能已经加入用户工程中，用户在gaf package支持的各个平台下编译出来的包或者执行程序都能够支持gaf功能模块了。

### Package的结构

一个完整的package应该包括package.json和install.json两个json文件；另外，还应该包括其他需要添加到用户工程中的文件。

package的所有文件都放在一个目录下，在发布时，将整个目录打包为zip文件并上传到服务器上供用户下载安装。


### package.json文件说明

package.json文件是对一个package内容的简单描述。对pmr来说，它的主要作用让pmr知道package的名称、版本信息及支持的引擎版本等，使pmr能支持这个package查找与安装。

以gaf package为例，它的package.json文件内容如下：
```
{
	"name": "gaf",
	"version": "3.0",
	"engine": "3.1.1+",
	"author": "GAFMEDIA",
	"url": "http://gafmedia.com/",
	"description": "GAF is ..."
}
```
由上可见，package.json的内容由以下几项组成：
- name: package 的名称
- version: package 的版本
- engine: package 支持的引擎版本
- author: package 的作者
- url: package 的技术支持网页
- description: 对这个 package 的简单说明

### install.json文件说明

install.json定义了将package添加到用户工程中时，需要做的工作。它包括一个指令列表，在运行"cocos framework add <包名>"指令时，pmr将读取install.json，按照指令列表逐一执行，执行结束后，package添加到用户工程的工作也随之完成。

install.json的典型结构如下：
```
[
	{
		"command": "add_project",
		"name": "quick_libs",
		"platform": "android"
	},
	{
		"command": "add_system_framework",
		"name": "SystemConfiguration.framework",
		....(略)
		"platform": "mac"
	},
	{
		"command": "add_files_and_dir",
		....(略)
	},
	{
		"command": "add_entry_function",
		"declare": "void package_quick_register();"
	}
]
```

目前install.json支持以下指令(command)：
- add_project: 添加一个工程文件到用户的工程中。支持android、win、mac_ios平台。添加到每个平台时，需要单独的add_project指令，不能够合并到同一个指令中。

**\[THE END\]**