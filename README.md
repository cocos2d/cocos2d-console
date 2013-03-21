cocos2d-js
==========

## Download

```sh
$ NOT DONE YET
```

## Install

```sh
$ NOT DONE YET
```

## What is cocos2d-js ?

cocos2d is a family of game engines for different platforms and written in different languages. These engines share the same features.

But cocos2d-js is NOT just another cocos2d engine. Instead it is a package... or a meta-package or a meta-project... or a collection of different components and engines tailored for iOS, Android and Web game development. cocos2d-js includes:

  * [cocos2d-x](http://github.com/cocos2d/cocos2d-x)
  * [Chipmunk](https://github.com/slembcke/Chipmunk-Physics)
  * JavaScript bindings for cocos2d-x and Chipmunk
  * [cocos2d-html5](http://github.com/cocos2d/cocos2d-html5) 
  * [Chipmunk-JS](http://github.com/josephg/Chipmunk-js)
  * CocosPlayer
  * [CocosBuilder](http://github.com/cocos2d/CocosBuilder)
  * ...with an installer (although the installer is not ready yet).


cocos2d-js has a JavaScript API. This API can be used both on mobile (iOS and Android) and Web Browsers.
 - For mobile it uses C++ / C (cocos2d-x and Chipmunk) with JavaScript bindings.
 - For Web it uses JavaScript (cocos2d-html5 and Chipmunk-JS).


### Mini FAQ

#### Is cocos2d-js a JavaScript engine ?

*Short answer:* No or Yes.  
*Longer answer:* cocos2d-js is not an engine, but a collection of engines and compoents. For Web it uses cocos2d-html5 and Chipmunk-JS, and they are JavaScript engines. 
But for mobile it uses cocos2d-x and Chipmunk (which are C++ and C engines) with JavaScript bindings.

#### Does my JavaScript code runs both on mobile and Web ?

*Short answer:* Yes  
*Longer answer:* If you stick to the cocos2d-js API, then your code is going to portable between Web and Mobile. All of our tests (more than 400) and our games are portable between Web and Mobile without changing a single line of code.
You should use our API and avoid using HTML5 APIs, which are not part of our mobile solution.

#### Can I use a mobile Web brower to run my games ?
Yes you can.

#### If so, why do I need the C / C++ with JS bindings engines ?
Because our C++ / C with JS bindings engines run 10 times faster than our 100% JS engines.  
If you are targenting mobile, we strongly recommend packaging your game using our C / C++ with JS bindings engines.

#### What's the difference between cocos2d-js, cocos2d-html5 and cocos2d-JavaScript ?

- cocos2d-js is this meta-project.
- [cocos2d-html5](http://github.com/cocos2d/cocos2d-html5) is in implementation of cocos2d in JavaScript, developed by the cocos2d-html5 / cocos2d-x communities. It is part of this meta-project.
- [cocos2d-JavaScript](http://www.cocos2d-javascript.org/) is another implementation of cocos2d in JavaScript, developed by Ryan Williams. But it is NOT part of this meta-project.

#### Can I use cocos2d-iphone instead of cocos2d-x ?
Yes you can, but you should know that cocos2d-iphone only works on iOS and not on Android.  


