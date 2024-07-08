import ezdxf

def read_all_lines(file_path: str) -> list:
    entities = []
    doc = ezdxf.readfile(file_path)
    modelspace = doc.modelspace()
    for entity in modelspace:
        print(type(entity).__name__)
        # if type(entity).__name__ == 'Insert':
        #     block = doc.blocks[entity.dxf.name]
        #     for block_entity in block:
        #         entities.append(type(block_entity).__name__)
        # else:
        #     entities.append(type(entity).__name__)
    return entities


r = read_all_lines('assets/lamp.dxf')
print(r)