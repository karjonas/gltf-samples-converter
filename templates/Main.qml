pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D
import QtQuick3D.Helpers

Window {
    id: window
    width: 1280
    height: 720
    visible: true
    title: qsTr("Hello World")

    property bool configLoaded: false

    QtObject {
        id: configData
        property bool lmEnabled: false
        property int lmSamples: 256
        property int lmResolution: 512
        property string model: ""
        property int modelScaleFactor: 1
        property double modelYPos: 0
        property double lightRotationX: 0
        property double lightRotationY: 0
        property double lightBrightness: 1
    }

     QtObject {
         id: configLogic

        function extractBaseName(path) {
            var normalized = path.replace(/\\/g, "/")
            var fileName = normalized.split("/").pop()
            var dotIndex = fileName.lastIndexOf(".")
            return dotIndex >= 0 ? fileName.slice(0, dotIndex) : fileName
        }

         function getConfigPath() {
             const args = Qt.application.arguments;
             const index = args.indexOf("--");
             if (index !== -1 && index + 1 < args.length) {
                 let path = args[index + 1];
                 return Qt.resolvedUrl(path);
             }
             return "";
         }

         function loadConfig() {
             let configPath = getConfigPath()
             if (!configPath) {
                 console.warn("No -- path/to/config.json argument provided");
                 return;
             }

             let xhr = new XMLHttpRequest();
             xhr.open("GET", configPath);
             xhr.onreadystatechange = function () {
                 if (xhr.readyState === XMLHttpRequest.DONE) {
                     if (xhr.status === 200) {
                         try {
                             let baseConfig = JSON.parse(xhr.responseText);
                             if (baseConfig["model"]) {
                                var modelKey = extractBaseName(baseConfig.model);
                                if (baseConfig[modelKey]) {
                                    let modelConfig = baseConfig[modelKey];
                                    for (let key in modelConfig)
                                        baseConfig[key] = modelConfig[key];
                                }
                             }

                             configData.lmEnabled = baseConfig.lmEnabled;
                             configData.lmSamples = baseConfig.lmSamples;
                             configData.lmResolution = baseConfig.lmResolution;
                             configData.model = baseConfig.model;
                             configData.modelScaleFactor = baseConfig.modelScaleFactor;
                             configData.modelYPos = baseConfig.modelYPos;
                             configData.lightRotationX = baseConfig.lightRotationX;
                             configData.lightRotationY = baseConfig.lightRotationY;
                             configData.lightBrightness = baseConfig.lightBrightness;

                             window.configLoaded = true;
                         } catch (e) {
                             console.error("Failed to parse JSON config:", e);
                         }
                     } else {
                         console.error("Failed to load config, status:", xhr.status, xhr.statusText);
                     }
                 }
             };
             xhr.send();
         }
     }

    Component.onCompleted: {
        configLogic.loadConfig();
    }


    View3D {
        id: view3d
        anchors.fill: parent
        focus: true

        environment: SceneEnvironment {
            clearColor: "#808080"
            backgroundMode: SceneEnvironment.Color
            lightmapper: Lightmapper {
                samples: configData.lmSamples
            }
        }

        // Light

        DirectionalLight {
            bakeMode: configData.lmEnabled ? Light.BakeModeAll : Light.BakeModeDisabled
            y: 400
            eulerRotation.x: configData.lightRotationX
            eulerRotation.y: configData.lightRotationY
            shadowMapQuality: Light.ShadowMapQualityVeryHigh
            pcfFactor: 1
            castsShadow: true
            shadowFactor: 100
            brightness: configData.lightBrightness
        }

        PerspectiveCamera {
            id: camera
            z: 300
            y: 100
        }

        // Floor

        Model {
            source: "#Rectangle"
            scale: Qt.vector3d(15, 15, 15)
            eulerRotation.x: -90
            materials: [
                PrincipledMaterial {
                    baseColor: Qt.rgba(0.8, 0.8, 0.9, 1.0)
                }
            ]
            usedInBakedLighting: configData.lmEnabled
            lightmapBaseResolution: configData.lmResolution
            bakedLightmap: BakedLightmap {
                enabled: configData.lmEnabled
                key: "rectangle"
                loadPrefix: "file:"
            }
        }

        // Model

        Loader3D {
            id: modelLoader
            active: window.configLoaded && configData.model !== ""
            source: configData.model
            onLoaded: {
                if (modelLoader.item) {
                    modelLoader.item.bakingEnabled = configData.lmEnabled;
                    modelLoader.item.lightmapBaseResolution = configData.lmResolution;
                    modelLoader.item.position.y = configData.modelYPos;

                    let scaleFactor = configData.modelScaleFactor;
                    modelLoader.item.scale = Qt.vector3d(
                        modelLoader.item.scale.x * scaleFactor,
                        modelLoader.item.scale.y * scaleFactor,
                        modelLoader.item.scale.z * scaleFactor
                    );
                }
            }
        }

        WasdController {
            controlledObject: camera
        }

        // UI

        RowLayout {
            anchors.fill: parent

            Page {
                Layout.preferredWidth: 250
                Layout.fillHeight: true

                ScrollView {
                    anchors.fill: parent
                    padding: 10

                    ColumnLayout {
                        CheckBox {
                            id: lmEnabled
                            checked: configData.lmEnabled
                            text: "Lightmaps enabled: " + configData.lmEnabled
                            onCheckedChanged: configData.lmEnabled = checked
                        }

                        Text {
                            text: "Lightmap resolution: " + configData.lmResolution.toFixed(2)
                        }
                        Slider {
                            id: resolutionSlider
                            value: configData.lmResolution
                            from: 0
                            to: 2048
                            onValueChanged: configData.lmResolution = value
                        }

                        Text {
                            text: "Light X: " + configData.lightRotationX.toFixed(2)
                        }
                        Slider {
                            id: rotationXSlider
                            value: configData.lightRotationX
                            from: -180
                            to: 180
                            onValueChanged: configData.lightRotationX = value
                        }

                        Text {
                            text: "Light Y: " + configData.lightRotationY.toFixed(2)
                        }
                        Slider {
                            id: rotationYSlider
                            value: configData.lightRotationY
                            from: -180
                            to: 180
                            onValueChanged: configData.lightRotationY = value
                        }
                        Text {
                            text: "Brightness: " + configData.lightBrightness.toFixed(2)
                        }
                        Slider {
                            id: brightnessSlider
                            value: configData.lightBrightness
                            from: 0
                            to: 10
                            onValueChanged: configData.lightBrightness = value
                        }
                    }
                }
            }
        }

        Item {
            width: debugViewToggleText.implicitWidth
            height: debugViewToggleText.implicitHeight
            anchors.right: parent.right
            Label {
                id: debugViewToggleText
                text: "Click here " + (dbg.visible ? "to hide DebugView" : "for DebugView")
                color: "white"
                anchors.right: parent.right
                anchors.top: parent.top
            }
            MouseArea {
                anchors.fill: parent
                onClicked: dbg.visible = !dbg.visible
                DebugView {
                    y: debugViewToggleText.height * 2
                    anchors.right: parent.right
                    source: view3d
                    id: dbg
                    visible: false
                }
            }
        }
    }
}
