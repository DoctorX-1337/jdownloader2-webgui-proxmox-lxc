import pytest
from backend.app.download_folders import destination, folder_name


def test_package_template_stays_below_nas_root():
    assert destination('/mnt/downloads/') == '/mnt/downloads/<jd:packagename>'


@pytest.mark.parametrize('value', ['../Film', '..', '/etc/passwd', 'Film: Test?', 'CON', 'A'*500, 'ä'*300])
def test_folder_names_are_single_safe_portable_components(value):
    name = folder_name(value)
    assert name and name not in ('.','..') and '/' not in name and '\\' not in name
    assert not any(char in name for char in ':*?"<>|')
    assert len(name.encode()) <= 220


def test_normal_package_name_is_preserved():
    assert folder_name('Meine.Serie.Staffel.1') == 'Meine.Serie.Staffel.1'
