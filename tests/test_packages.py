from copy import deepcopy

import pytest

from backend.app.packages import summarize


def file(ident, package='10', **values):
    return {'uuid':str(ident), 'packageUUID':str(package), 'enabled':True, **values}


def test_package_progress_is_weighted_and_includes_finished_parts():
    links=[file(1,bytesTotal=100,bytesLoaded=100,finished=True),file(2,bytesTotal=900,bytesLoaded=0)]
    row,=summarize([{'uuid':10,'name':'Multi-part archive','bytesLoaded':100,'bytesTotal':1000,'enabled':True}],links,'RUNNING')
    assert row['progress']==10
    assert row['finishedCount']==1 and row['fileCount']==2
    assert row['bytesTotal']==1000 and row['bytesLoaded']==100


def test_native_package_totals_handle_mirrors_and_use_byte_based_eta():
    links=[file(1,bytesTotal=1000,bytesLoaded=500),file(2,bytesTotal=1000,bytesLoaded=0)]
    row,=summarize([{'uuid':10,'bytesLoaded':500,'bytesTotal':1000,'speed':100,'running':True,'enabled':True}],links,'RUNNING')
    assert row['progress']==50 and row['bytesTotal']==1000
    assert row['eta']==5 and row['speed']==100 and row['status']=='running'


def test_same_names_are_grouped_by_id_and_input_is_not_changed():
    packages=[{'uuid':10,'name':'Same name','bytesLoaded':25,'bytesTotal':100,'enabled':True},{'uuid':11,'name':'Same name','bytesLoaded':75,'bytesTotal':100,'enabled':True}]
    links=[file(1,package=10,bytesTotal=100),file(2,package=11,bytesTotal=100)]
    before=deepcopy((packages,links))
    rows=summarize(packages,links,'RUNNING')
    assert [row['uuid'] for row in rows]==['10','11']
    assert [row['progress'] for row in rows]==[25,75]
    assert (packages,links)==before


def test_unknown_total_does_not_report_a_false_percentage():
    links=[file(1,bytesLoaded=100,bytesTotal=100,finished=True),file(2,bytesLoaded=10,bytesTotal=-1)]
    row,=summarize([{'uuid':10,'bytesTotal':100,'bytesLoaded':110,'enabled':True}],links,'RUNNING')
    assert row['progress'] is None and row['unknownSizeCount']==1
    assert row['bytesLoaded']==110


@pytest.mark.parametrize('controller,package',[
    ('PAUSE',{'enabled':True}),('RUNNING',{'enabled':False}),
])
def test_paused_package_has_no_running_speed_or_eta(controller,package):
    row,=summarize([{'uuid':10,'bytesTotal':100,'bytesLoaded':50,'running':True,'speed':10,'eta':5,**package}],[file(1,bytesTotal=100)],controller)
    assert row['status']=='paused' and row['speed']==0 and row['eta']==0


def test_extraction_remains_visible_after_download_has_finished():
    row,=summarize([{'uuid':10,'bytesTotal':100,'bytesLoaded':100,'finished':True}],[file(1,bytesTotal=100,finished=True,extractionStatus='RUNNING')],'RUNNING')
    assert row['status']=='extracting' and row['finished'] and row['progress']==100
    assert row['finishedCount']==row['fileCount']==1


def test_extraction_error_and_skipped_links_are_not_reported_as_success():
    row,=summarize([{'uuid':10,'finished':True}],[file(1,finished=True,extractionStatus='ERROR_PW')],'IDLE')
    assert row['status']=='extraction_error'
    row,=summarize([{'uuid':10,'enabled':True}],[file(1,skipped=True,bytesTotal=100)],'IDLE')
    assert row['status']=='attention' and row['problemCount']==1


def test_orphan_links_are_visible_and_empty_packages_are_omitted():
    row,=summarize([{'uuid':10,'name':'Empty'}],[file(1,package=12,bytesTotal=100,bytesLoaded=25)],'IDLE')
    assert row['uuid']=='12' and row['progress']==25 and row['fileCount']==1


def test_native_totals_are_clamped_without_inventing_completion():
    row,=summarize([{'uuid':10,'bytesLoaded':120,'bytesTotal':100,'enabled':True}],[file(1,bytesTotal=100)],'RUNNING')
    assert row['progress']==100 and not row['finished']
