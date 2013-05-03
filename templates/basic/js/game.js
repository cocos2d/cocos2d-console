//
// $PROJECT_NAME$
//
// $LICENSE$
//

//
// Game Layer
//
var GameLayer = cc.Layer.extend({

    ctor:function (game_state) {
        this._super();
        this.init();
    }
});


//------------------------------------------------------------------
//
// Main entry point - JSB
//
//------------------------------------------------------------------
// "mobile" and "desktop" are valid alternatives here
if (sys.platform !== "browser") {
    function run() {

        audioEngine = cc.AudioEngine.getInstance();
        director = cc.Director.getInstance();
        winSize = director.getWinSize();
        centerPos = cc.p(winSize.width / 2, winSize.height / 2);

        // Tell CocosBuilderReader to load
        cc.BuilderReader.setResourcePath("res/CCB/");

        var scene = cc.Scene.create();

        // main menu
        var menu = new BootLayer();
        scene.addChild(menu);

        var runningScene = director.getRunningScene();
        if (runningScene === null)
            director.runWithScene(scene);
        else
            director.replaceScene(cc.TransitionFade.create(0.5, scene));
    }

    run();
}

//------------------------------------------------------------------
//
// Main entry point - html5
//
//------------------------------------------------------------------

var WaterMelonScene = cc.Scene.extend({
    ctor:function () {
        this._super();
        //these variables will be declared as global variable
        audioEngine = cc.AudioEngine.getInstance();
        director = cc.Director.getInstance();
        winSize = director.getWinSize();
        centerPos = cc.p(winSize.width / 2, winSize.height / 2);
        sizeRatio = winSize.width / 480;

        // Tell CocosBuilderReader to load
        cc.BuilderReader.setResourcePath("res/CCB/");

        //var menu = new BootLayer();
        var menu = new BootLayer();
        //var menu = new OptionsLayer();
        this.addChild(menu);
        this.setPosition(cc.p(0, 0));
    }
});
