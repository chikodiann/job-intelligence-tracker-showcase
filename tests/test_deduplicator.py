from job_monitor.db.storage import JobStorage
from job_monitor.ingestion.deduplicator import JobDeduplicator
from job_monitor.models import NormalizedJob


def test_deduplicator_layer_1_source_id():
    storage = JobStorage(db_path=":memory:")
    job1 = NormalizedJob(
        source_name="remotive",
        external_id="101",
        url="https://remotive.com/101",
        title="DevOps Lead",
        company_name="CloudCo",
        content_hash="hash_devops_1",
        canonical_fingerprint="cloudco|devops lead|worldwide"
    )
    storage.save_normalized_job(job1)

    dedup = JobDeduplicator(storage=storage)
    res = dedup.check_duplicate(job1)
    assert res.is_duplicate is True
    assert res.match_level == "SOURCE_ID"


def test_deduplicator_layer_2_url():
    storage = JobStorage(db_path=":memory:")
    job1 = NormalizedJob(
        source_name="remotive",
        external_id="101",
        url="https://company.com/careers/job1",
        title="DevOps Lead",
        company_name="CloudCo",
        content_hash="hash_devops_1",
        canonical_fingerprint="cloudco|devops lead|worldwide"
    )
    storage.save_normalized_job(job1)

    job2 = NormalizedJob(
        source_name="jobicy",
        external_id="jobicy-999",
        url="https://company.com/careers/job1",
        title="DevOps Lead",
        company_name="CloudCo",
        content_hash="hash_different",
        canonical_fingerprint="cloudco|devops lead|worldwide"
    )

    dedup = JobDeduplicator(storage=storage)
    res = dedup.check_duplicate(job2)
    assert res.is_duplicate is True
    assert res.match_level == "URL"


def test_deduplicator_batch_dedup():
    storage = JobStorage(db_path=":memory:")
    dedup = JobDeduplicator(storage=storage)

    job1 = NormalizedJob(
        source_name="remotive",
        external_id="1",
        url="https://remotive.com/1",
        title="Python Dev",
        company_name="PyCorp",
        content_hash="hash1",
        canonical_fingerprint="pycorp|python dev|worldwide"
    )
    job2 = NormalizedJob(
        source_name="remotive",
        external_id="2",
        url="https://remotive.com/1", # Duplicate URL
        title="Python Dev",
        company_name="PyCorp",
        content_hash="hash1",
        canonical_fingerprint="pycorp|python dev|worldwide"
    )

    uniques, duplicates = dedup.deduplicate([job1, job2])
    assert len(uniques) == 1
    assert len(duplicates) == 1
    assert uniques[0].external_id == "1"
