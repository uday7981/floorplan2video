from __future__ import annotations

import pytest

from video_worker.providers import SubmitRequest
from video_worker.providers.together import TogetherVideoProvider, encode_png_data_url


def test_submit_frames_only(fake_together_success, tiny_png_bytes):
    p = TogetherVideoProvider(_client=fake_together_success)
    req = SubmitRequest(
        prompt="x",
        resolution="480p",
        duration_s=4,
        start_frame_url=encode_png_data_url(tiny_png_bytes),
        end_frame_url=encode_png_data_url(tiny_png_bytes),
    )
    sr = p.submit(req)
    assert sr.provider_job_id == "job_test"
    call = fake_together_success.calls_create[0]
    assert call["model"] == "ByteDance/Seedance-2.5"
    assert call["resolution"] == "480p"
    assert call["seconds"] == "4"
    assert "frame_images" in call["media"]
    assert len(call["media"]["frame_images"]) == 2


def test_submit_rejects_combined_frames_and_reference_video(fake_together_success, tiny_png_bytes):
    p = TogetherVideoProvider(_client=fake_together_success)
    req = SubmitRequest(
        prompt="x",
        resolution="480p",
        duration_s=4,
        start_frame_url=encode_png_data_url(tiny_png_bytes),
        end_frame_url=encode_png_data_url(tiny_png_bytes),
        reference_video_url="https://example.invalid/clip.mp4",
    )
    with pytest.raises(ValueError, match="forbids combining"):
        p.submit(req)


def test_submit_rejects_missing_frames(fake_together_success):
    p = TogetherVideoProvider(_client=fake_together_success)
    req = SubmitRequest(prompt="x", resolution="480p", duration_s=4)
    with pytest.raises(ValueError, match="start_frame_url"):
        p.submit(req)


def test_poll_succeeded(fake_together_success):
    p = TogetherVideoProvider(_client=fake_together_success)
    pr = p.poll("job_test")
    assert pr.status == "succeeded"
    assert pr.output_url == "https://example.invalid/out.mp4"


def test_poll_failed(fake_together_failure):
    p = TogetherVideoProvider(_client=fake_together_failure)
    pr = p.poll("job_fail")
    assert pr.status == "failed"
    assert "validation" in (pr.error or "")


def test_encode_png_data_url_prefix(tiny_png_bytes):
    url = encode_png_data_url(tiny_png_bytes)
    assert url.startswith("data:image/png;base64,")
