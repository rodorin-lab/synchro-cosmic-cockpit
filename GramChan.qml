import QtQuick

Item {
    id: root
    width: 120
    height: 150
    property string mood: "normal"

    SequentialAnimation on y {
        loops: Animation.Infinite
        NumberAnimation { to: y + 6; duration: 1400; easing.type: Easing.InOutSine }
        NumberAnimation { to: y - 6; duration: 1400; easing.type: Easing.InOutSine }
    }

    Rectangle {
        id: body
        anchors.horizontalCenter: parent.horizontalCenter
        y: 80
        width: 100
        height: 45
        radius: 22
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#ff007f" }
            GradientStop { position: 1.0; color: "#800040" }
        }
        border.color: "#ffd700"
        border.width: 2

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            spacing: 10
            Repeater {
                model: 3
                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: index === 1 ? "#00f0ff" : "#ffd700"
                    SequentialAnimation on opacity {
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 500 + index * 200 }
                        NumberAnimation { to: 1.0; duration: 500 + index * 200 }
                    }
                }
            }
        }
    }

    Rectangle {
        id: dome
        anchors.horizontalCenter: parent.horizontalCenter
        y: 32
        width: 85
        height: 55
        radius: 42
        color: "#0d0d20"
        border.color: "#00f0ff"
        border.width: 2
        opacity: 0.95
    }

    Rectangle {
        id: antennaStem
        anchors.horizontalCenter: parent.horizontalCenter
        y: 12
        width: 3
        height: 22
        color: "#ffd700"
        transformOrigin: Item.Bottom

        RotationAnimation on rotation {
            loops: Animation.Infinite
            from: -20
            to: 20
            duration: 250
        }

        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            y: -6
            width: 14
            height: 14
            radius: 7
            color: "#ff007f"
            border.color: "#ffd700"
            border.width: 1

            SequentialAnimation on scale {
                loops: Animation.Infinite
                NumberAnimation { to: 1.4; duration: 300 }
                NumberAnimation { to: 1.0; duration: 300 }
            }
        }
    }

    Row {
        anchors.horizontalCenter: dome.horizontalCenter
        y: dome.y + 22
        spacing: 16

        Rectangle {
            width: mood === "sleep" ? 10 : (mood === "happy" ? 12 : 10)
            height: mood === "sleep" ? 3 : (mood === "happy" ? 6 : 10)
            radius: mood === "sleep" ? 0 : 5
            color: mood === "sad" ? "#ff007f" : "#00f0ff"
            border.color: "#ffffff"
            border.width: 1
        }

        Rectangle {
            width: mood === "sleep" ? 10 : (mood === "happy" ? 12 : 10)
            height: mood === "sleep" ? 3 : (mood === "happy" ? 6 : 10)
            radius: mood === "sleep" ? 0 : 5
            color: mood === "sad" ? "#ff007f" : "#00f0ff"
            border.color: "#ffffff"
            border.width: 1
        }
    }

    Rectangle {
        anchors.horizontalCenter: dome.horizontalCenter
        y: dome.y + 38
        width: mood === "happy" ? 20 : (mood === "sad" ? 6 : 12)
        height: mood === "happy" ? 10 : (mood === "sad" ? 3 : 5)
        radius: mood === "happy" ? 10 : (mood === "sad" ? 0 : 3)
        color: mood === "happy" ? "#ff007f" : "transparent"
        border.color: "#ff007f"
        border.width: 2
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 130
        width: 80
        height: 10
        radius: 5
        color: "#000000"
        opacity: 0.4
    }

    Repeater {
        model: mood === "sleep" ? 3 : 0
        Text {
            text: "z"
            color: "#00f0ff"
            font.pixelSize: 12 + index * 5
            x: root.width - 15 + index * 10
            y: 5 - index * 12
            opacity: 0.6

            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { to: 0; duration: 1200 + index * 400 }
                NumberAnimation { to: 0.6; duration: 400 }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (mood === "normal" || mood === "sleep") mood = "happy";
            else mood = "normal";
            jumpAnim.start();
        }
    }

    SequentialAnimation {
        id: jumpAnim
        NumberAnimation { target: root; property: "y"; to: root.y - 35; duration: 180; easing.type: Easing.OutQuad }
        NumberAnimation { target: root; property: "y"; to: root.y; duration: 180; easing.type: Easing.InQuad }
    }
}
