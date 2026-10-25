from backend.app.extraction import from_link, for_package


def native(current=40,total=100,eta=7500):
    return {'PluginProgress':{'id':'EXTRACTION','current':current,'total':total,'eta':eta,'label':'Extracting...'},'ExtractionStatus':{'id':'RUNNING'}}


def test_native_extraction_percent_and_millisecond_eta_are_preserved():
    item=from_link({},native())
    assert item['state']=='running' and item['progress']==40
    assert item['bytesProcessed']==40 and item['bytesTotal']==100
    assert item['eta']==7


def test_download_progress_is_not_used_as_extraction_progress():
    item=from_link({'extractionStatus':'RUNNING'},{'PluginProgress':{'id':'DOWNLOAD','current':95,'total':100,'eta':1200}})
    assert item['progress'] is None and item['bytesProcessed']==0
    assert item['eta']==0


def test_unknown_extraction_total_is_not_reported_as_complete():
    item=from_link({},native(40,0,-1))
    assert item['progress'] is None and item['eta']==0


def test_success_and_password_error_have_explicit_status():
    done=from_link({'extractionStatus':'SUCCESSFUL'}, {})
    assert done['state']=='finished' and done['progress']==100
    failed=from_link({'extractionStatus':'ERROR_PW'}, {})
    assert failed['state']=='error' and failed['progress'] is None
    assert failed['label']=='Entpackpasswort erforderlich'


def test_repeated_rar_parts_do_not_multiply_extracted_bytes():
    item=from_link({},native())
    result=for_package([{'extraction':dict(item)} for _ in range(16)])
    assert result['bytesProcessed']==40 and result['bytesTotal']==100
    assert result['progress']==40


def test_missing_extraction_status_does_not_invent_an_extraction():
    assert from_link({}, {}) is None
    assert for_package([{'finished':True}]) is None
