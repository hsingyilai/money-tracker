"""A QTreeWidget that mirrors an anytree category tree.

The old code hand-rolled the anytree -> QTreeWidget sync in four places
(``InputWindow`` and ``CategoriesWindow``, once to build and once to reload).
This widget owns that sync so there is a single copy of it.
"""
from anytree import LevelOrderIter, Node, PreOrderIter
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from .styles import TREE_WIDGET


class CategoryTreeItem(QTreeWidgetItem):
    """A tree row that keeps a link back to its anytree node."""

    def __init__(self):
        super().__init__()
        self.anytree_node: Node | None = None


class CategoryTree(QTreeWidget):
    def __init__(self, root: Node, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setStyleSheet(TREE_WIDGET)
        self._root = root
        self._items: list[CategoryTreeItem] = []
        self.rebuild()

    def set_root(self, root: Node) -> None:
        self._root = root
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the whole widget from the current anytree root."""
        self.clear()
        self._items = []
        for i, node in enumerate(LevelOrderIter(self._root)):
            item = CategoryTreeItem()
            item.setText(0, node.name)
            item.anytree_node = node
            node.index = i  # back-pointer used while wiring up children
            self._items.append(item)

        for node in LevelOrderIter(self._root):
            for child in node.children:
                self._items[node.index].addChild(self._items[child.index])

        self.addTopLevelItem(self._items[0])
        self.setCurrentItem(self._items[0])
        self._items[0].setExpanded(True)

    # -- reading -----------------------------------------------------------
    def current_node(self) -> Node | None:
        item = self.currentItem()
        return item.anytree_node if item is not None else None

    def select_node(self, node: Node) -> None:
        self.setCurrentItem(self._items[node.index])

    def select_by_name(self, name: str) -> None:
        for node in PreOrderIter(self._root):
            if node.name == name:
                self.select_node(node)
                return

    # -- editing ---------------------------------------------------------
    def add_child(self, parent_node: Node, name: str, **attrs) -> Node:
        """Add a child under ``parent_node`` and select it."""
        new_node = Node(name, parent=parent_node, **attrs)
        new_node.index = len(self._items)

        item = CategoryTreeItem()
        item.setText(0, name)
        item.anytree_node = new_node
        self._items[parent_node.index].addChild(item)
        self._items.append(item)

        self.select_node(new_node)
        return new_node

    def remove_current(self) -> Node | None:
        """Detach the selected node from the tree and return it."""
        item = self.currentItem()
        if item is None:
            return None
        node = item.anytree_node
        node.parent = None
        parent_item = item.parent()
        if parent_item is not None:
            parent_item.removeChild(item)
        self.clearSelection()
        return node
