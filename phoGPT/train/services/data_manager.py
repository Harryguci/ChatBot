from datasets import load_dataset, DatasetDict, Dataset
from typing import Optional, Union, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataManager:
    """
    DataManager service to handle loading and managing datasets using the HuggingFace datasets library.
    """

    def __init__(self):
        self.dataset: Optional[Union[DatasetDict, Dataset]] = None
        self.dataset_name: Optional[str] = None

    def load_data(
        self,
        source: str,
        split: Optional[str] = None,
        cache_dir: Optional[str] = None,
        **kwargs
    ) -> Union[DatasetDict, Dataset]:
        """
        Load dataset from a specified source.

        Args:
            source: Dataset name from HuggingFace Hub or local path
            split: Optional specific split to load (e.g., 'train', 'test')
            cache_dir: Optional directory to cache downloaded datasets
            **kwargs: Additional arguments to pass to load_dataset

        Returns:
            Loaded dataset (DatasetDict or Dataset)
        """
        try:
            logger.info(f"Loading dataset from: {source}")
            dataset = load_dataset(
                source,
                split=split,
                cache_dir=cache_dir,
                **kwargs
            )
            if dataset is None:
                raise ValueError(f"Failed to load dataset from {source}")

            self.dataset = dataset
            self.dataset_name = source
            logger.info(f"Successfully loaded dataset: {source}")
            return self.dataset
        except Exception as e:
            logger.error(f"Error loading dataset from {source}: {str(e)}")
            raise

    def get_dataset_info(self) -> Dict[str, Any]:
        """
        Get information about the currently loaded dataset.

        Returns:
            Dictionary containing dataset information
        """
        if self.dataset is None:
            raise ValueError("No dataset loaded. Call load_data() first.")

        info = {
            "dataset_name": self.dataset_name,
            "type": type(self.dataset).__name__,
        }

        if isinstance(self.dataset, DatasetDict):
            info["splits"] = list(self.dataset.keys())
            info["split_sizes"] = {
                split: len(data) for split, data in self.dataset.items()
            }
            # Get features from first available split
            first_split = list(self.dataset.keys())[0]
            info["features"] = str(self.dataset[first_split].features)
        else:
            info["size"] = len(self.dataset)
            info["features"] = str(self.dataset.features)

        return info

    def get_split(self, split_name: str) -> Dataset:
        """
        Get a specific split from the dataset.

        Args:
            split_name: Name of the split to retrieve

        Returns:
            Dataset for the specified split
        """
        if self.dataset is None:
            raise ValueError("No dataset loaded. Call load_data() first.")

        if isinstance(self.dataset, DatasetDict):
            if split_name not in self.dataset:
                raise ValueError(
                    f"Split '{split_name}' not found. Available splits: {list(self.dataset.keys())}"
                )
            return self.dataset[split_name]
        else:
            logger.warning("Dataset is not split. Returning entire dataset.")
            return self.dataset

    def print_dataset_info(self) -> None:
        """
        Print detailed information about the loaded dataset.
        """
        if self.dataset is None:
            print("No dataset loaded.")
            return

        print("=" * 80)
        print("DATASET INFORMATION")
        print("=" * 80)
        print(f"\nDataset: {self.dataset_name}")

        if isinstance(self.dataset, DatasetDict):
            print(f"Splits: {list(self.dataset.keys())}")

            for split_name, split_data in self.dataset.items():
                print(f"\n{str(split_name).upper()} Split:")
                print(f"  Number of examples: {len(split_data)}")
                print(f"  Features: {split_data.features}")

                if len(split_data) > 0:
                    print(f"\n  First example from {str(split_name)}:")
                    first_example = split_data[0]
                    for key, value in first_example.items():
                        if isinstance(value, str) and len(value) > 200:
                            print(f"    {key}: {value[:200]}...")
                        else:
                            print(f"    {key}: {value}")
        else:
            print(f"Size: {len(self.dataset)}")
            print(f"Features: {self.dataset.features}")

            if len(self.dataset) > 0:
                print("\nFirst example:")
                first_example = self.dataset[0]
                for key, value in first_example.items():
                    if isinstance(value, str) and len(value) > 200:
                        print(f"  {key}: {value[:200]}...")
                    else:
                        print(f"  {key}: {value}")

        print("\n" + "=" * 80)

    def get_num_examples(self, split: Optional[str] = None) -> int:
        """
        Get the number of examples in the dataset or a specific split.

        Args:
            split: Optional split name

        Returns:
            Number of examples
        """
        if self.dataset is None:
            raise ValueError("No dataset loaded. Call load_data() first.")

        if split:
            return len(self.get_split(split))
        elif isinstance(self.dataset, DatasetDict):
            return sum(len(data) for data in self.dataset.values())
        else:
            return len(self.dataset)

    def filter_dataset(
        self,
        filter_fn,
        split: Optional[str] = None
    ) -> Union[Dataset, DatasetDict]:
        """
        Filter the dataset using a custom function.

        Args:
            filter_fn: Function that takes an example and returns True/False
            split: Optional split name to filter (if None, filters all splits)

        Returns:
            Filtered dataset
        """
        if self.dataset is None:
            raise ValueError("No dataset loaded. Call load_data() first.")

        if split:
            filtered = self.get_split(split).filter(filter_fn)
            logger.info(f"Filtered {split} split: {len(filtered)} examples remaining")
            return filtered
        elif isinstance(self.dataset, DatasetDict):
            filtered_dict = {
                name: data.filter(filter_fn)
                for name, data in self.dataset.items()
            }
            logger.info("Filtered all splits")
            return DatasetDict(filtered_dict)
        else:
            filtered = self.dataset.filter(filter_fn)
            logger.info(f"Filtered dataset: {len(filtered)} examples remaining")
            return filtered

    def map_dataset(
        self,
        map_fn,
        split: Optional[str] = None,
        batched: bool = False,
        **kwargs
    ) -> Union[Dataset, DatasetDict]:
        """
        Apply a mapping function to the dataset.

        Args:
            map_fn: Function to apply to each example
            split: Optional split name to map (if None, maps all splits)
            batched: Whether to process in batches
            **kwargs: Additional arguments for the map function

        Returns:
            Mapped dataset
        """
        if self.dataset is None:
            raise ValueError("No dataset loaded. Call load_data() first.")

        if split:
            return self.get_split(split).map(map_fn, batched=batched, **kwargs)
        elif isinstance(self.dataset, DatasetDict):
            return DatasetDict({
                name: data.map(map_fn, batched=batched, **kwargs)
                for name, data in self.dataset.items()
            })
        else:
            return self.dataset.map(map_fn, batched=batched, **kwargs)