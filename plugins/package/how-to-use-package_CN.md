# Package 使用说明

package 是 pmr 的管理对象。一个完整的 package 在放到 pmr 服务器上后，用户即可通过 pmr 命令行指令查找、下载和安装此 package 到本机上。安装完成的 package ，可以在用户需要时通过命令行添加到用户的工程中，扩展用户工程的功能模块。

### Package 的安装使用

以 gaf 这个package为例，在 cocos2d-x 的环境配置好了以后，即可用以下命令进行操作。

安装：

```sh
cocos package install gaf
```
安装成功后，进入用户的工程目录，用以下命令将 package 加入用户工程：

```sh
cocos framework add gaf
```
如果运行一切正常，gaf 模块的功能已经加入用户工程中，用户在 gaf package 支持的各个平台下编译出来的包或者执行程序都能够支持 gaf 功能模块了。

### Package 的结构

一个完整的 package 应该包括 package.json 和 install.json 两个 json 文件；另外，还应该包括其他需要添加到用户工程中的文件。

package 的所有文件都放在一个目录下，在发布时，将整个目录打包为zip文件并上传到服务器上供用户下载安装。


### package.json 文件说明

package.json 文件是对一个 package 的内容的简单描述。对 pmr 来说，它的主要作用让 pmr 知道 package 的名称、版本信息及支持的引擎版本等，使 pmr 能支持这个 package 查找与安装。

以 gaf package 为例，它的 package.json 文件内容如下：
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
由上可见，package.json 的内容由以下几项组成：
- name: package 的名称
- version: package 的版本
- engine: package 支持的引擎版本
- author: package 的作者
- url: package 的技术支持网页
- description: 对这个 package 的简单说明

### install.json 文件说明

install.json 定义了将 package 添加到用户工程中时，需要做的工作。它包括一个指令列表，在运行 "cocos framework add <包名>" 指令时，pmr 将读取 install.json ，按照指令列表逐一执行，执行结束后， package 添加到用户工程的工作也随之完成。

install.json 的典型结构如下：
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

目前 install.json 支持以下指令( command )：
- add_project: 添加一个工程文件到用户的工程中。支持 android、win、ios_mac 平台。添加到每个平台时，需要单独的 add_project 指令，不能够合并到同一个指令中。各个平台的 add_project 指令所需要其他参数有所不同。
  -  name: 指定工程名，每个平台的 add_project 指令都需要有这个参数
  -  platform: 指定当前 add_project 指令要处理的平台，必需，只有 "android"、"win"、"ios_mac" 三个值可选
  -  其他：win 平台和 ios_mac 平台还需要其他一些额外的参数，主要是定义各个工程项的 ID 值。为了简化配置，pmr 提供了用命令行自动生成和配置这些 ID 的方法，请参考"通过模板创建 package "的相关说明。
  
- add_header_path：添加一个头文件搜索路径到用户的工程中。支持 android、win、ios、mac 平台。通常各个平台需要添加的头文件搜索路径是相同的，所以可以共用一个指令。此指令的格式示例如下：
```
	{
		"command": "add_header_path",
		"source": "gaf-3.0/include",
		"platform": ["ios", "mac", "win", "android"]
	}
```

-  add_lib: 添加一个库到用户的工程中。支持 android、win、ios、mac 平台。由于各个平台需要添加的库文件不可能使用同一个，所以无法共用一个指令。此指令的格式示例如下，请注意 andriod 平台需要的参数有所不同：
```
	{
		"command": "add_lib",
		"source": "gaf-3.0/prebuild/ios/libgafplayer.a",
		"platform": ["ios"]
	},
	{
		"command": "add_lib",
		"source": "gaf-3.0/prebuild/mac/libgafplayer.a",
		"platform": ["mac"]
	},
	{
		"command": "add_lib",
		"source": "gaf-3.0/prebuild/win32/vs2013/gafplayer.lib",
		"platform": ["win"]
	},
	{
		"command": "add_lib",
		"source": "gafplayer_static",
		"import-module": "gaf-3.0/prebuild/android",
		"platform": ["android"]
	}
```

-   add_system_framework：添加一个系统的 framework 到用户的工程中。只支持 ios 和 mac 平台。此命令需要一些具体的参数，下面会有简单说明；具体的配置方法，可以参考"通过模板创建 package "的相关说明。
    - name：要添加的 framework 的名称
    - file_id：framework 的文件 id
    - path:  framework 文件的引用路径
    - sourceTree：framework 所属的源的类型
    - id：framework 在工程里的 id
    - platform：当前指令要操作的平台，只能是 "ios" 或者 "mac"
    - 示例如下：  
```
	{
		"command": "add_system_framework",
		"name": "SystemConfiguration.framework",
		"file_id": "DABC994D1A82109100BF5CC4",
		"path": "System/Library/Frameworks/SystemConfiguration.framework",
		"sourceTree": "SDKROOT",
		"id": "DABC994E1A82109100BF5CC4",
		"platform": "mac"
	},
	{
		"command": "add_system_framework",
		"name": "SystemConfiguration.framework",
		"file_id": "DABC99501A8214A100BF5CC4",
		"path": "Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS8.1.sdk/System/Library/Frameworks/SystemConfiguration.framework",
		"sourceTree": "DEVELOPER_DIR",
		"id": "DABC99511A8214A100BF5CC4",
		"platform": "ios"
	}
```

-   add_files_and_dir：添加文件和目录到用户工程中。此命令不区分平台。通常用于脚本文件的复制。
    -  backup_if_override：设置在复制时如果原来工程有相同文件是否备份。可选值为 true 或者 false 。
    -  source：要复制的文件名和目录名的列表
    -  src_dir：从哪个目录进行复制，注意此目录以 package 所在目录为基准
    -  dst_dir：要复制到哪个目录下，注意此目录以用户工程目录为基准
    -  假设用户工程目录为 /User/proj ，安装名为 quickui 、版本号为 1.0 的一个 package ，在安装时 package 所在目录必定为 /User/proj/packages/quickui-1.0 。以下第一条指令将 /User/proj/packages/quickui-1.0/files_to_copy/quick 复制到 /User/proj/src/scripts 目录下，覆盖相同文件时不备份；第二条指令将 /User/proj/packages/quickui-1.0/files_to_copy 目录下的几个文件复制到 /User/proj/src 目录下，覆盖相同文件前先改名进行备份：
```
	{
		"command": "add_files_and_dir",
		"backup_if_override": false,
		"source": [
			"quick"
		],
		"src_dir": "files_to_copy",
		"dst_dir": "src/scripts"
	},
	{
		"command": "add_files_and_dir",
		"backup_if_override": true,
		"source": [
			"main.lua",
			"config.lua",
			"app/MyApp.lua",
			"app/scenes/MainScene.lua"
		],
		"src_dir": "files_to_copy",
		"dst_dir": "src"
	}
```

-  add_entry_function：将模块的入口函数添加到用户的工程中。这条命令不区分平台，参数只有一个 "declare" ，用于指定入口函数的声明语句。入口函数的参数和返回值都必须是 void 。示例如下：
```
	{
		"command": "add_entry_function",
		"declare": "void package_quickui_register();"
	}
```

### 通过模板创建 package

在制作较复杂的 package 时，特别是制作带有源代码的 package，install.json 中指令的配置有可能会比较复杂。为了简化这一部分工作，pmr 提供了 package 的创建模板。以下将以创建一个名为 test 的 package 为例，说明用模板创建一个 package 的过程。

#### 1. 创建用户工程

由于 package 是直接安装于用户工程的，所以创建 package 也必须在用户工程中进行创建和修改，最后才能得到可用于安装的 package 包。

这一步就是创建一个正常的 cocos 工程，所使用的命令和普通 cocos 工程的创建并没有什么不同：
```
cocos new myproj -p com.user.myproj -l lua -d /Users/home/projects
cd /Users/home/projects/myproj
```

创建完成后，如上命令，我们需要进入工程目录下，进行下一步的工作。

#### 2. 创建新的 package

运行以下命令创建一个新的 package：
```
cocos framework create test
```
运行成功后，用户工程目录下会生成 packages/test-1.0 目录，此目录下就是新的 package 的内容。

目录下有以下文件及目录：
-  package.json：如前所述，这是 package 的描述文件。里面的内容较简单，可以自己打开查看和修改。
-  install.json：如前所述，这是 package 的安装指令描述文件。目前里面已经有三条安装指令。
    - android 平台的 "add_project" 指令：通常这条指令不需要再作修改了
    - ios_mac 平台的 "add_project" 指令：这条指令如果用户自己配置的话会比较麻烦，因此模板自动用 UUID 库随机生成了各项 id 的参数值，通常情况下已经能很好的使用，不需要再作修改。如果自动配置的各 id 在加入到用户的 ios_mac 平台工程里时，确实与原有的其他项的id有冲突的话，可以另外再建一个 package ，将重新生成的 id 复制过来。
    - add_entry_function 指令：通常这条指令也不需要再作修改

-  package_test_register.cpp：这个文件里定义了 package 的入口调用函数，创建时只有一个空函数。可以自己修改函数的内容。
-  proj.android：此目录下存放 android 工程文件。可以自己修改文件的内容。
-  proj.ios_mac：此目录下存放 ios_mac 工程文件。可以自己修改文件的内容。
-  proj.win32：此目录下存放 win 工程文件。可以自己修改文件的内容。

#### 3. 设置自定义安装指令

##### "add_project" for win32

在刚创建的新 package 的 install.json 里并没有 win 平台的 "add_project" 指令。这是一般都需要有的指令，pmr 的 framework set 命令可以帮助添加这条指令。

首先用 VS2012 或者 VS2013打开 frameworks/runtime-src/proj.win32 下的 myproj.sln，将 packages/test-1.0/proj.win32 目录下的 test.vcxproj 工程添加到 myproj 工程中。此时系统将为 test 工程在 myproj 工程中分配标识 id，我们需要将 id 提取出来。将 myproj 工程保存并退出 VS，在工程目录下，运行命令：
```
cocos framework set test
```
现在打开 packages/test-1.0/install.json，可以看到已经添加了win平台的"add_project"指令，大致如下：
```
	{
		"command": "add_project",
		"name": "test",
		"project_id": "8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942",
		"build_id": "59411DD0-24F9-48F7-80EA-3F8000855168",
		"platform": "win"
	}
```

##### "add_system_framework"

在 ios/mac 工程里，我们有时需要添加某个系统的 framework 库以支持 package 的功能，此时我们需要手动配置一下 add_system_framework 指令。

以添加 "SystemConfiguration.framework" 这个 framework 到mac工程中为例。首先用Xcode打开 frameworks/runtime-src/proj.ios_mac 下的 myproj.xcodeproj ，添加 SystemConfiguration.framework 到 mac 工程中，退出 Xcode 。用文本编辑器在 frameworks/runtime-src/proj.ios_mac/myproj.xcodeproj/project.pbxproj 中搜索字串 "SystemConfiguration.framework" ，找到以下类似内容的行：
```
DABC994D1A82109100BF5CC4 /* SystemConfiguration.framework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.framework; name = SystemConfiguration.framework; path = System/Library/Frameworks/SystemConfiguration.framework; sourceTree = SDKROOT; };
```
根据这一行，可以配置以下参数：

```
"name": "SystemConfiguration.framework",
"file_id": "DABC994D1A82109100BF5CC4",
"path": "System/Library/Frameworks/SystemConfiguration.framework",
"sourceTree": "DEVELOPER_DIR",
```

接下来以 file_id 的值 "DABC99501A8214A100BF5CC4" 进行搜索，可以找到以下类似内容的行：
```
DABC994E1A82109100BF5CC4 /* SystemConfiguration.framework in Frameworks */ = {isa = PBXBuildFile; fileRef = DABC994D1A82109100BF5CC4 /* SystemConfiguration.framework */; };
```
根据这一行，可以配置以下参数：
```
"id": "DABC994E1A82109100BF5CC4",
```
最后，可以在 install.json 中添加以下指令了：
```
	{
		"command": "add_system_framework",
		"name": "SystemConfiguration.framework",
		"file_id": "DABC994D1A82109100BF5CC4",
		"path": "System/Library/Frameworks/SystemConfiguration.framework",
		"sourceTree": "SDKROOT",
		"id": "DABC994E1A82109100BF5CC4",
		"platform": "mac"
	},
```

ios 平台的 add_system_framework 指令的添加与上述过程类似。

##### 其他指令

其他指令的参数比较明确，可以直接参考各条指令的说明，不再详述。


#### 4. 添加其他文件

经过前面的步骤之后，我们已经得到了一个能够正常安装的 package，只需要将 test-1.0 目录压缩成 zip 包，就可以发布 test 这个 package 了。

但是，这个 package 只有一个空的入口，没有任何功能。实际的 package ，当然是需要实现一定的功能的。这样，就需要在 package 里加入需要的其他文件，如可能会有 test.cpp、test.h、mylib.a 等等。将这些文件复制到 packages/test-1.0 下，可以按你希望的目录结构来存放。接下来，可以在 packages/test-1.0 下的各个平台的工程文件中，分别添加对以上文件的引用，并修改各相关文件保证编译能够正常通过。

以上步骤都完成后，一个新的 package 就制作完成了。


**\[THE END\]**