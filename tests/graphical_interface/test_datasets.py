"""Adding datasets and moving through the runs."""
import os

from PySide6 import QtCore

from gui import live_result


def test_a_folder_of_runs_becomes_a_dataset_and_its_first_run_is_shown(
        window, qtbot, data_root):
    with live_result(window, qtbot):
        window.sidebar.add_paths([os.path.join(data_root, "pbar_scan")])
    s = window.s
    assert [d.name for d in s.datasets] == ["pbar_scan"]
    assert [i.run_number for i in s.datasets[0].items] == [517890, 517891, 517892]
    assert s.current == (s.datasets[0], s.datasets[0].items[0])
    tree = window.sidebar.tree
    assert tree.isVisible() and tree.topLevelItemCount() == 1
    assert tree.topLevelItem(0).childCount() == 3
    assert window.sidebar.summary.text() == "3 images, 0 counted"
    assert window.run_btn.isEnabled()


def test_each_dataset_gets_its_own_colour_and_marker(loaded):
    ds = loaded.s.datasets
    assert [d.name for d in ds] == ["pbar_scan", "background", "ions"]
    assert len({d.colour for d in ds}) == 3 and len({d.symbol for d in ds}) == 3


def test_adding_the_same_folder_twice_gives_a_second_name(window, qtbot,
                                                         data_root):
    with live_result(window, qtbot):
        window.sidebar.add_paths([os.path.join(data_root, "background")])
    window.sidebar.add_paths([os.path.join(data_root, "background")])
    assert [d.name for d in window.s.datasets] == ["background", "background-2"]


def test_loose_images_are_added_one_item_per_file(window, qtbot, data_root):
    folder = os.path.join(data_root, "loose_images")
    files = [os.path.join(folder, f) for f in sorted(os.listdir(folder))]
    with live_result(window, qtbot):
        window.sidebar.add_paths(files)
    assert len(window.s.datasets[0].items) == 2


def test_an_empty_folder_adds_nothing_and_says_so(window, tmp_path):
    logged = []
    window.s.logged.connect(lambda level, msg: logged.append((level, msg)))
    window.sidebar.add_paths([str(tmp_path)])
    assert window.s.datasets == []
    assert logged and logged[-1][0] == "warn"


def test_clicking_a_run_in_the_list_makes_it_current(loaded, qtbot):
    win = loaded
    ds = win.s.datasets[1]                           # background
    node = win.sidebar._nodes[ds.items[1].path]
    with live_result(win, qtbot):
        win.sidebar.tree.setCurrentItem(node)
    assert win.s.current == (ds, ds.items[1])
    assert win.s.live.item is ds.items[1]


def test_page_down_and_page_up_step_through_the_runs_across_datasets(
        loaded, qtbot):
    win = loaded
    flat = [it for d in win.s.datasets for it in d.items]
    assert win.s.current[1] is flat[0]
    for k in (1, 2, 3):                              # 3 = first background run
        with live_result(win, qtbot):
            qtbot.keyClick(win, QtCore.Qt.Key_PageDown)
        assert win.s.current[1] is flat[k]
    assert win.s.current[0].name == "background"
    with live_result(win, qtbot):
        qtbot.keyClick(win, QtCore.Qt.Key_PageUp)
    assert win.s.current[1] is flat[2]
    win.sidebar.step(-10)                            # stops at the first
    assert win.s.current[1] is flat[0]


def test_the_filter_hides_the_runs_that_do_not_match(loaded):
    win = loaded
    win.sidebar.filter.setText("517891")
    top = win.sidebar.tree.topLevelItem(0)
    assert [top.child(j).isHidden() for j in range(3)] == [True, False, True]
    win.sidebar.filter.setText("")
    assert not any(top.child(j).isHidden() for j in range(3))


def test_removing_the_current_dataset_clears_the_view(loaded):
    win = loaded
    win.s.remove(win.s.datasets[0])
    assert [d.name for d in win.s.datasets] == ["background", "ions"]
    assert win.s.current is None and win.s.live is None
