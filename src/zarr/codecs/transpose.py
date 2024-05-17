from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from zarr.buffer import NDBuffer
from zarr.codecs.mixins import ArrayArrayCodecBatchMixin
from zarr.codecs.registry import register_codec
from zarr.common import JSON, ArraySpec, ChunkCoordsLike, parse_named_configuration

if TYPE_CHECKING:
    from typing import TYPE_CHECKING

    from typing_extensions import Self


def parse_transpose_order(data: JSON | Iterable[int]) -> tuple[int, ...]:
    if not isinstance(data, Iterable):
        raise TypeError(f"Expected an iterable. Got {data} instead.")
    if not all(isinstance(a, int) for a in data):
        raise TypeError(f"Expected an iterable of integers. Got {data} instead.")
    return tuple(cast(Iterable[int], data))


@dataclass(frozen=True)
class TransposeCodec(ArrayArrayCodecBatchMixin):
    is_fixed_size = True

    order: tuple[int, ...]

    def __init__(self, *, order: ChunkCoordsLike) -> None:
        order_parsed = parse_transpose_order(order)

        object.__setattr__(self, "order", order_parsed)

    @classmethod
    def from_dict(cls, data: dict[str, JSON]) -> Self:
        _, configuration_parsed = parse_named_configuration(data, "transpose")
        return cls(**configuration_parsed)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, JSON]:
        return {"name": "transpose", "configuration": {"order": list(self.order)}}

    def evolve(self, array_spec: ArraySpec) -> Self:
        if len(self.order) != array_spec.ndim:
            raise ValueError(
                f"The `order` tuple needs have as many entries as there are dimensions in the array. Got {self.order}."
            )
        if len(self.order) != len(set(self.order)):
            raise ValueError(
                f"There must not be duplicates in the `order` tuple. Got {self.order}."
            )
        if not all(0 <= x < array_spec.ndim for x in self.order):
            raise ValueError(
                f"All entries in the `order` tuple must be between 0 and the number of dimensions in the array. Got {self.order}."
            )
        order = tuple(self.order)

        if order != self.order:
            return replace(self, order=order)
        return self

    def resolve_metadata(self, chunk_spec: ArraySpec) -> ArraySpec:
        from zarr.common import ArraySpec

        return ArraySpec(
            shape=tuple(chunk_spec.shape[self.order[i]] for i in range(chunk_spec.ndim)),
            dtype=chunk_spec.dtype,
            fill_value=chunk_spec.fill_value,
            order=chunk_spec.order,
        )

    async def decode_single(
        self,
        chunk_array: NDBuffer,
        chunk_spec: ArraySpec,
    ) -> NDBuffer:
        inverse_order = [0] * chunk_spec.ndim
        for x, i in enumerate(self.order):
            inverse_order[x] = i
        chunk_array = chunk_array.transpose(inverse_order)
        return chunk_array

    async def encode_single(
        self,
        chunk_array: NDBuffer,
        chunk_spec: ArraySpec,
    ) -> NDBuffer | None:
        chunk_array = chunk_array.transpose(self.order)
        return chunk_array

    def compute_encoded_size(self, input_byte_length: int, _chunk_spec: ArraySpec) -> int:
        return input_byte_length


register_codec("transpose", TransposeCodec)
