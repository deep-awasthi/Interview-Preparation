# Architecture Overview

Aether adheres to Clean Architecture principles, ensuring that business logic is independent of frameworks, databases, and external interfaces.

## Layer Structure

```
+-------------------------------------------------------+
|  Presentation Layer (Plain Django HTTP REST Views)   |
+-------------------------------------------------------+
                           |
                           v
+-------------------------------------------------------+
|  Application & Domain Services                        |
|  (BucketService, ObjectService, MultipartService)     |
+-------------------------------------------------------+
              |                             |
              v                             v
+-----------------------------+ +-----------------------+
| Repositories / PostgreSQL   | | BaseStorageDriver     |
| (Metadata & Audit Logs)     | | (FilesystemDriver)    |
+-----------------------------+ +-----------------------+
```

### Storage Driver Contract

```python
class BaseStorageDriver(ABC):
    @abstractmethod
    def save(self, bucket: str, key: str, data: BinaryIO | bytes | Iterable[bytes]) -> Tuple[int, str]: pass
    @abstractmethod
    def read(self, bucket: str, key: str, range_start: Optional[int], range_end: Optional[int]) -> Generator[bytes, None, None]: pass
    @abstractmethod
    def delete(self, bucket: str, key: str) -> bool: pass
```
