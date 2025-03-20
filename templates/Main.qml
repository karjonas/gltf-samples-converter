import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D
import QtQuick3D.Helpers

Window {
    width: 1280
    height: 720
    visible: true
    title: qsTr("Hello World")

    View3D {
        id: root
        anchors.fill: parent

        // Lm props
        property bool lmEnabled: appConfig["lmEnabled"]
        property int lmSamples: appConfig["lmSamples"]
        property int lmResolution: appConfig["lmResolution"]

        // Model props
        property string model: appConfig["model"]
        property int modelScaleFactor: appConfig["modelScaleFactor"]
        property double modelYPos: appConfig["modelYPos"]

        // Light props
        property double lightRotationX: appConfig["lightRotationX"]
        property double lightRotationY: appConfig["lightRotationY"]
        property double lightBrightness: appConfig["lightBrightness"]

        Component.onCompleted: console.log("Model Path:", root.model)

        environment: SceneEnvironment {
            clearColor: "#808080"
            backgroundMode: SceneEnvironment.Color
            lightmapper: Lightmapper {
                samples: root.lmSamples
            }
        }

        // Light

        DirectionalLight {
            bakeMode: root.lmEnabled ? Light.BakeModeAll : Light.BakeModeDisabled
            y: 400
            eulerRotation.x: root.lightRotationX
            eulerRotation.y: root.lightRotationY
            shadowMapQuality: Light.ShadowMapQualityVeryHigh
            pcfFactor: 1
            castsShadow: true
            shadowFactor: 100
            brightness: root.lightBrightness
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
            usedInBakedLighting: root.lmEnabled
            lightmapBaseResolution: root.lmResolution
            bakedLightmap: BakedLightmap {
                enabled: root.lmEnabled
                key: "rectangle"
                loadPrefix: "file:"
            }
        }

        // Model

        Loader3D {
            id: modelLoader
            source: "qrc:/" + root.model + "/" + root.model + ".qml"
            onLoaded: {
                if (modelLoader.item) {
                    modelLoader.item.bakingEnabled = root.lmEnabled;
                    modelLoader.item.lightmapBaseResolution = root.lmResolution;
                    modelLoader.item.position.y = root.modelYPos;

                    let scaleFactor = root.modelScaleFactor;
                    modelLoader.item.scale = Qt.vector3d(
                        modelLoader.item.scale.x * scaleFactor,
                        modelLoader.item.scale.y * scaleFactor,
                        modelLoader.item.scale.z * scaleFactor
                    );
                }
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
                        text: "Lightmaps enabled: " + root.lmEnabled
                        onCheckedChanged: root.lmEnabled = checked
                        Component.onCompleted: checked = root.lmEnabled
                    }

                    Text {
                        text: "Lightmap resolution: " + root.lmResolution.toFixed(2)
                    }
                    Slider {
                        id: resolutionSlider
                        value: 256
                        from: 0
                        to: 2048
                        onValueChanged: root.lmResolution = value
                        Component.onCompleted: resolutionSlider.value = root.lmResolution
                    }

                    Text {
                        text: "Light X: " + root.lightRotationX.toFixed(2)
                    }
                    Slider {
                        id: rotationXSlider
                        value: -135
                        from: -180
                        to: 180
                        onValueChanged: root.lightRotationX = value
                        Component.onCompleted: rotationXSlider.value = root.lightRotationX
                    }

                    Text {
                        text: "Light Y: " + root.lightRotationY.toFixed(2)
                    }
                    Slider {
                        id: rotationYSlider
                        value: -90
                        from: -180
                        to: 180
                        onValueChanged: root.lightRotationY = value
                        Component.onCompleted: rotationYSlider.value = root.lightRotationY
                    }
                    Text {
                        text: "Brightness: " + root.lightBrightness.toFixed(2)
                    }
                    Slider {
                        id: brightnessSlider
                        value: 5
                        from: 0
                        to: 10
                        onValueChanged: root.lightBrightness = value
                        Component.onCompleted: brightnessSlider.value = root.lightBrightness
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
                source: root
                id: dbg
                visible: false
            }
        }
    }
}
