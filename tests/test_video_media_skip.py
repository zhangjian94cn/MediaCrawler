# -*- coding: utf-8 -*-
"""Tests for skipping already-downloaded videos."""

import pytest

from store.bilibili.bilibilli_store_media import BilibiliVideo
from store.douyin.douyin_store_media import DouYinVideo
from store.xhs.xhs_store_media import XiaoHongShuVideo


@pytest.mark.asyncio
async def test_bilibili_save_video_skips_existing_file(tmp_path):
    store = BilibiliVideo()
    store.video_store_path = str(tmp_path)

    aid = 123456
    file_path = tmp_path / str(aid) / "video.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = b"existing-video-content"
    file_path.write_bytes(original_content)

    await store.save_video(aid, b"new-video-content", "video.mp4")

    assert store.video_exists(aid, "video.mp4") is True
    assert file_path.read_bytes() == original_content


@pytest.mark.asyncio
async def test_bilibili_video_exists_ignores_empty_file(tmp_path):
    store = BilibiliVideo()
    store.video_store_path = str(tmp_path)

    aid = 123456
    file_path = tmp_path / str(aid) / "video.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"")

    assert store.video_exists(aid, "video.mp4") is False


@pytest.mark.asyncio
async def test_xhs_save_video_skips_existing_file(tmp_path):
    store = XiaoHongShuVideo()
    store.video_store_path = str(tmp_path)

    note_id = "test_note_id"
    file_path = tmp_path / note_id / "0.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = b"existing-note-video-content"
    file_path.write_bytes(original_content)

    await store.save_video(note_id, b"new-note-video-content", "0.mp4")

    assert store.video_exists(note_id, "0.mp4") is True
    assert file_path.read_bytes() == original_content


@pytest.mark.asyncio
async def test_xhs_video_exists_ignores_empty_file(tmp_path):
    store = XiaoHongShuVideo()
    store.video_store_path = str(tmp_path)

    note_id = "test_note_id"
    file_path = tmp_path / note_id / "0.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"")

    assert store.video_exists(note_id, "0.mp4") is False


@pytest.mark.asyncio
async def test_douyin_save_video_skips_existing_file(tmp_path):
    store = DouYinVideo()
    store.video_store_path = str(tmp_path)

    aweme_id = "123456789"
    title = "test-title"
    file_path = tmp_path / f"{title}_{aweme_id}.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = b"existing-douyin-video-content"
    file_path.write_bytes(original_content)

    await store.save_video(aweme_id, b"new-douyin-video-content", title)

    assert store.video_exists(aweme_id, title) is True
    assert file_path.read_bytes() == original_content


@pytest.mark.asyncio
async def test_douyin_save_video_overwrites_empty_file(tmp_path):
    store = DouYinVideo()
    store.video_store_path = str(tmp_path)

    aweme_id = "123456789"
    title = "test-title"
    file_path = tmp_path / f"{title}_{aweme_id}.mp4"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"")

    new_content = b"new-douyin-video-content"
    await store.save_video(aweme_id, new_content, title)

    assert file_path.read_bytes() == new_content
