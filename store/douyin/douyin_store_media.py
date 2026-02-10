# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/douyin_store_media.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils


class DouYinImage(AbstractStoreImage):
    image_store_path: str = "data/douyin/images"

    async def store_image(self, image_content_item: Dict):
        """
        store content

        Args:
            image_content_item:

        Returns:

        """
        await self.save_image(image_content_item.get("aweme_id"), image_content_item.get("pic_content"), image_content_item.get("extension_file_name"))

    def make_save_file_name(self, aweme_id: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            aweme_id: aweme id
            extension_file_name: image filename with extension

        Returns:

        """
        return f"{self.image_store_path}/{aweme_id}/{extension_file_name}"

    async def save_image(self, aweme_id: str, pic_content: str, extension_file_name):
        """
        save image to local

        Args:
            aweme_id: aweme id
            pic_content: image content
            extension_file_name: image filename with extension

        Returns:

        """
        pathlib.Path(self.image_store_path + "/" + aweme_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(aweme_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[DouYinImageStoreImplement.save_image] save image {save_file_name} success ...")


class DouYinVideo(AbstractStoreVideo):
    # 默认路径，可通过环境变量 DOUYIN_VIDEO_SAVE_DIR 覆盖
    video_store_path: str = os.environ.get('DOUYIN_VIDEO_SAVE_DIR', 'data/douyin/videos')

    @staticmethod
    def sanitize_filename(title: str) -> str:
        """
        清理文件名中的非法字符
        Args:
            title: 原始标题
        Returns:
            清理后的文件名
        """
        import re
        # 移除或替换非法字符
        illegal_chars = r'[<>:"/\\|?*\n\r\t]'
        clean_title = re.sub(illegal_chars, '', title)
        # 限制长度（避免文件名过长）
        if len(clean_title) > 100:
            clean_title = clean_title[:100]
        # 移除首尾空格
        clean_title = clean_title.strip()
        # 如果清理后为空，使用默认名称
        if not clean_title:
            clean_title = "video"
        return clean_title

    def make_save_file_name(self, aweme_id: str, title: str) -> str:
        """
        生成保存文件的完整路径，使用标题命名
        Args:
            aweme_id: 视频ID
            title: 视频标题
        Returns:
            完整文件路径
        """
        clean_title = self.sanitize_filename(title)
        return f"{self.video_store_path}/{clean_title}_{aweme_id}.mp4"

    def video_exists(self, aweme_id: str, title: str) -> bool:
        """
        检查视频文件是否已存在（用于增量更新）
        Args:
            aweme_id: 视频ID
            title: 视频标题
        Returns:
            bool: 文件是否存在
        """
        save_file_name = self.make_save_file_name(aweme_id, title)
        file_path = pathlib.Path(save_file_name)
        if file_path.exists() and file_path.stat().st_size > 0:
            return True
        return False

    async def store_video(self, video_content_item: Dict):
        """
        store content

        Args:
            video_content_item:

        Returns:

        """
        aweme_id = video_content_item.get("aweme_id")
        title = video_content_item.get("title", "video")
        video_content = video_content_item.get("video_content")
        await self.save_video(aweme_id, video_content, title)

    async def save_video(self, aweme_id: str, video_content: bytes, title: str):
        """
        save video to local

        Args:
            aweme_id: aweme id
            video_content: video content
            title: 视频标题

        Returns:

        """
        # 确保目录存在
        pathlib.Path(self.video_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(aweme_id, title)

        # 检查文件是否已存在
        file_path = pathlib.Path(save_file_name)
        if file_path.exists() and file_path.stat().st_size > 0:
            utils.logger.info(f"[DouYinVideoStoreImplement.save_video] Video already exists, skipping: {save_file_name}")
            return

        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(video_content)
            utils.logger.info(f"[DouYinVideoStoreImplement.save_video] save video {save_file_name} success ...")
