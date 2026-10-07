from dataclasses import dataclass


@dataclass
class Grid:
    rows: int = 8
    cols: int = 8

    def get_cells(self, width: int, height: int):
        cells = []

        cell_width = width / self.cols
        cell_height = height / self.rows

        for row in range(self.rows):
            for col in range(self.cols):

                x = int(col * cell_width)
                y = int(row * cell_height)

                w = int(cell_width)
                h = int(cell_height)

                cells.append(
                    {
                        "id": row * self.cols + col,
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                    }
                )

        return cells