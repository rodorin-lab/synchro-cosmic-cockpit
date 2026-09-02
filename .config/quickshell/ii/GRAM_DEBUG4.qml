import Quickshell
import QtQuick
import "panelFamilies"

ShellRoot {
    PanelFamilyLoader {}
    component PanelFamilyLoader: LazyLoader {
        active: true
        component: IllogicalImpulseFamily {}
    }
}