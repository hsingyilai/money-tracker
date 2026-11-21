"""A list-row delegate that puts each row's check box in its top-left corner.

Qt draws the check box of a checkable list row in the middle of its left edge.
This delegate draws it in the top-left corner instead, and toggles it when it is
clicked there. The row's text has to be moved out of the way: give the rows a
left padding of ``text_indent()``.

The box is painted here rather than by the platform style: on macOS the native
check box only came out on the first row of the list.
"""
from PyQt6.QtCore import QEvent, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from . import styles


class TopLeftCheckDelegate(QStyledItemDelegate):
    SIZE = 18  # The check box is a square this many pixels wide.
    LEFT = 6  # From the row's left edge to the check box.
    TOP = 7  # From the row's top edge to the check box.
    GAP = 8  # Between the check box and the text.

    BORDER = QColor("#262626")  # The same dark outline as the app's buttons.
    FILL = QColor("white")
    FILL_CHECKED = QColor(styles.SELECTION_GREEN)
    TICK = QColor("white")

    def box_size(self, widget=None) -> int:
        return self.SIZE

    def text_indent(self, widget=None) -> int:
        """How far in from the row's left edge the text must start."""
        return self.LEFT + self.SIZE + self.GAP

    def check_rect(self, option: QStyleOptionViewItem) -> QRect:
        return QRect(option.rect.left() + self.LEFT, option.rect.top() + self.TOP, self.SIZE, self.SIZE)

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Qt must not draw its own check box (or reserve room for it).
        option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator

    @staticmethod
    def _checkable(index) -> bool:
        """Like Qt: a row has a check box when it is checkable and has a check
        state (a plain list item is checkable but has no state, so it has none)."""
        flags = index.flags()
        return bool(
            flags & Qt.ItemFlag.ItemIsUserCheckable
            and flags & Qt.ItemFlag.ItemIsEnabled
            and index.data(Qt.ItemDataRole.CheckStateRole) is not None
        )

    @staticmethod
    def _is_checked(index) -> bool:
        value = index.data(Qt.ItemDataRole.CheckStateRole)
        return value is not None and Qt.CheckState(int(value)) == Qt.CheckState.Checked

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not self._checkable(index):
            return
        checked = self._is_checked(index)
        box = QRectF(self.check_rect(option)).adjusted(1, 1, -1, -1)  # Room for the outline.
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.BORDER, 1.5))
        painter.setBrush(self.FILL_CHECKED if checked else self.FILL)
        painter.drawRoundedRect(box, 4, 4)
        if checked:
            painter.setPen(QPen(self.TICK, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            at = lambda x, y: QPointF(box.left() + x * box.width(), box.top() + y * box.height())
            painter.drawPolyline([at(0.22, 0.53), at(0.43, 0.73), at(0.78, 0.30)])
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
            and self._checkable(index)
            and self.check_rect(option).contains(event.position().toPoint())
        ):
            now = Qt.CheckState.Unchecked if self._is_checked(index) else Qt.CheckState.Checked
            return model.setData(index, now.value, Qt.ItemDataRole.CheckStateRole)
        return super().editorEvent(event, model, option, index)
