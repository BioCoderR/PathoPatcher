from cgi import test
import json
import os
import shutil
from tkinter import NO
import unittest
from pathlib import Path

import numpy as np
from torch import gt
import yaml
from numpy.testing import assert_almost_equal, assert_array_equal
from PIL import Image

from pathopatcher.cli import PreProcessingConfig, PreProcessingYamlConfig
from pathopatcher.patch_extraction.patch_extraction import PreProcessor
from pathopatcher.utils.logger import Logger
from pathopatcher.utils.tools import close_logger
from test_database.download import check_test_database


class TestPreProcessorBaseline(unittest.TestCase):
    """Test the PreProcessor Module with basic (default) parameter setup"""
    
    @classmethod
    def setUpClass(cls) -> None:    
        """Setup configuration"""
        check_test_database()
        cls.config = "./tests/static_test_files/preprocessing/roi_context/config.yaml"        
        with open(cls.config, "r") as config_file:
            yaml_config = yaml.safe_load(config_file)
            yaml_config = PreProcessingYamlConfig(**yaml_config)

        opt_dict = dict(yaml_config)
        cls.opt_dict = {k: v for k, v in opt_dict.items() if v is not None}
        cls.configuration = PreProcessingConfig(**cls.opt_dict)
        
        cls.gt_folder = Path(
            "./tests/static_test_files/preprocessing/roi_context/results/"
        ).resolve()
        cls.wsi_name = "JP2K-33003-1"
        
        preprocess_logger = Logger(
            level=cls.configuration.log_level.upper(),
            log_dir=cls.configuration.log_path,
            comment="preprocessing",
            use_timestamp=True,
        )
        cls.logger = preprocess_logger.create_logger()
        # do preprocessing for result checking
        cls.slide_processor = PreProcessor(slide_processor_config=cls.configuration)
        cls.logger.info(
            "Sucessfully started the setup - Now we calculate the base dataset. May take up to 10 Minutes!"
        )
        cls.slide_processor.sample_patches_dataset()

    @classmethod
    def tearDownClass(cls):
        """Clean output directory"""
        # close logger
        close_logger(cls.logger)

        # clean output directory
        clean_folders = [
            f for f in Path(cls.opt_dict["output_path"]).iterdir() if f.is_dir()
        ]
        for f in clean_folders:
            shutil.rmtree(f.resolve())
        clean_files = [
            f for f in Path(cls.opt_dict["output_path"]).iterdir() if f.is_file()
        ]
        for f in clean_files:
            os.remove(f.resolve())
        shutil.rmtree(f.parent.resolve())
            
    def test_context_wsi_size(self) -> None:
        """Test if patch size for WSI is correct"""
        patch_path = (
            self.slide_processor.config.output_path / self.wsi_name / "patches"
        )
        patch_path = [f for f in patch_path.iterdir() if f.suffix == ".png"][0]

        patch = np.array(Image.open(patch_path.resolve()))

        self.assertEqual(patch.shape, (256, 256, 3))

    
    def test_np_mask_amount(self) -> None:
        """Test if the number of masks is correct and just calculated for the roi"""
        gt_path = self.gt_folder / self.wsi_name / "masks"
        gt_num_masks = len([f for f in gt_path.glob("*.npy")])

        test_path = (
            self.slide_processor.config.output_path / self.wsi_name / "masks" 
        )
        test_num_masks = len([f for f in test_path.glob("*.npy")])
        
        self.assertEqual(gt_num_masks, test_num_masks)

    def test_np_mask_content(self) -> None:
        """Test if the number of masks is correct and just calculated for the roi"""
        gt_path = self.gt_folder / self.wsi_name / "masks" / "JP2K-33003-1_2_10_mask.npy"
        gt_masks = np.load(gt_path)
        test_path = (
            self.slide_processor.config.output_path / self.wsi_name / "masks" / "JP2K-33003-1_2_10_mask.npy"
        )
        test_masks = np.load(test_path)
                
        assert_almost_equal(gt_masks, test_masks)
    
    def test_context_patch_metadata(self) -> None:
        """Test if the patch metadata is correct for a context patch"""
        gt_path = self.gt_folder / self.wsi_name / "metadata" / "JP2K-33003-1_2_6.yaml"
        with open(gt_path, "r") as f:
            gt_context_patch_metadata = yaml.safe_load(f)
        
        test_path = (
            self.slide_processor.config.output_path / self.wsi_name / "metadata" / "JP2K-33003-1_2_6.yaml"
        )
        with open(test_path, "r") as f:
            test_context_patch_metadata = yaml.safe_load(f)
        
        self.assertDictEqual(gt_context_patch_metadata, test_context_patch_metadata)
    
    def test_metadata_wsi(self) -> None:
        gt_path = self.gt_folder / self.wsi_name / "metadata.yaml"
        with open(gt_path, "r") as config_file:
            yaml_config = yaml.safe_load(config_file)

        test_path = (
            self.slide_processor.config.output_path / self.wsi_name / "metadata.yaml"
        )
        with open(test_path, "r") as config_file:
            test_file = yaml.safe_load(config_file)

        self.assertEqual(yaml_config, test_file)
    
    def test_patch_results_wsi(self) -> None:
        """Test if patches are extracted the right way for WSI"""
        gt_path = self.gt_folder / self.wsi_name / "patch_metadata.json"
        with open(gt_path, "r") as config_file:
            patch_gt = json.load(config_file)
            patch_gt = sorted(patch_gt, key=lambda d: list(d.keys())[0])

        test_path = (
            self.slide_processor.config.output_path
            / self.wsi_name
            / "patch_metadata.json"
        )
        with open(test_path, "r") as config_file:
            test_file = json.load(config_file)
            test_file = sorted(test_file, key=lambda d: list(d.keys())[0])

        self.assertEqual(patch_gt, test_file)