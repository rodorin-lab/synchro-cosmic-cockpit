import QtQuick

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#02010a" }
            GradientStop { position: 0.5; color: "#0a0520" }
            GradientStop { position: 1.0; color: "#050210" }
        }
    }

    Canvas {
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            ctx.strokeStyle = "rgba(0, 240, 255, 0.06)";
            ctx.lineWidth = 1;
            var gridSize = 50;
            for (var x = 0; x < width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (var y = 0; y < height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }
        }
    }

    Repeater {
        model: 60
        Rectangle {
            width: Math.random() * 3 + 1
            height: width
            radius: width / 2
            color: Math.random() > 0.7 ? "#ff007f" : (Math.random() > 0.5 ? "#00f0ff" : "#ffffff")
            x: Math.random() * parent.width
            y: Math.random() * parent.height
            opacity: 0

            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { to: Math.random() * 0.9 + 0.1; duration: Math.random() * 2000 + 800 }
                NumberAnimation { to: 0; duration: Math.random() * 2000 + 800 }
            }
        }
    }

    Repeater {
        model: 8
        Rectangle {
            width: Math.random() * 100 + 50
            height: 1
            color: "#00f0ff"
            opacity: 0.15
            x: Math.random() * parent.width
            y: Math.random() * parent.height

            SequentialAnimation on x {
                loops: Animation.Infinite
                NumberAnimation { to: x + 30; duration: Math.random() * 4000 + 3000 }
                NumberAnimation { to: x - 30; duration: Math.random() * 4000 + 3000 }
            }
        }
    }
}
