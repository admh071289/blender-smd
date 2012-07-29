import uuid, struct, array

_null = struct.pack("b",0)

def _get_string(datamodel,string,use_str_dict = True):
	dict_index = -1
	if use_str_dict:
		try: dict_index = datamodel.str_dict.index(string)
		except ValueError: pass
	if dict_index != -1:
		return struct.pack("i",dict_index)
	else:
		return bytes(string,'ASCII') + _null

class _Array:
	list = []
	type = None
	type_str = ""
	
	def __init__(self,list=None):
		if list:
			for item in list:
				if type(item) != self.type:
					raise TypeError("List must contain only {} values".format(self.type))
			self.list = list
	
	def tobytes(self, datamodel, elem):
		return array.array(self.type_str,self.list).tobytes()

class _BoolArray(_Array):
	type = bool
	type_str = "b"
class _IntArray(_Array):
	type = int
	type_str = "i"
class _FloatArray(_Array):
	type = float
	type_str = "f"
class _StrArray(_Array):
	type = str	
	def tobytes(self, datamodel, elem):
		out = bytes()
		for item in self.list:
			out += _get_string(datamodel,item,use_str_dict=False)
		return out
class _ElementArray(_Array):
	def __init__(self,list=None):
		self.type = Element
		_Array.__init__(self,list)
	def tobytes(self, datamodel, elem):
		out = []
		for item in self.list:
			out.append(datamodel.elem_index.index(item))
		return array.array("i",out).tobytes()
		
class _VectorArray(_Array):
	type = list
	def __init__(self,list=None):
		_Array.__init__(self,list)
		if list:
			for item in list:
				if len(item) != len(self.type_str):
					raise TypeError("All sequences must have {} items".format(len(self.type_str)))
					for ordinate in item:
						if type(ordinate) != float:
							raise TypeError("Sequences must contain only float values")	
	def tobytes(self, datamodel, elem):
		out = bytes()
		for item in self.list:
			for ordinate in range(len(self.type_str)):
				out += struct.pack("f",item[ordinate])
		return out
class _Vector2Array(_VectorArray):
	type_str = "ff"
class _Vector3Array(_VectorArray):
	type_str = "fff"
class _Vector4Array(_VectorArray):
	type_str = "ffff"
class _QuaternionArray(_Vector4Array):
	pass
	
class _AngleArray(_Vector3Array):
	pass
class _MatrixArray():
	pass
	
class _BinaryArray(_Array):
	pass
class _TimeArray(_FloatArray):
	pass
class _ColorArray(_Vector3Array):
	pass
		
class _Vector:
	list = []
	type_str = ""
	def __init__(self,list):
		if len(list) != len(self.type_str):
			raise ValueError("Expected list of {} floats".format(len(self.type_str)))
		self.list = list
	def tobytes(self):
		out = bytes()
		for ord in self.list:
			out += struct.pack("f",ord)
		return out
		
class Vector2(_Vector):
	type_str = "ff"
class Vector3(_Vector):
	type_str = "fff"
class Vector4(_Vector):
	type_str = "ffff"
class Quaternion(Vector4):
	pass
	
class Angle(Vector3):
	pass
class Matrix:
	pass

class Binary():
	pass
class Time(float):
	pass
class Color(Vector4):
	pass

class Property:
	_dmxtype = [None,"Element",int,float,bool,str,Binary,Time,Color,Vector2,Vector3,Vector4,Angle,Quaternion,Matrix,
				_ElementArray,_IntArray,_FloatArray,_BoolArray,_StrArray,_BinaryArray,_TimeArray,_ColorArray,_Vector2Array,_Vector3Array,_Vector4Array,_AngleArray,_QuaternionArray,_MatrixArray]
	value = None
	
	def __init__(self,name,value):
		if type(name) != str or not type(value) in self._dmxtype:
			raise TypeError("Expected str, {}",self._dmxtype)
		self.name = name
		self.value = value
	
	def typeid(self):
		return self._dmxtype.index(type(self.value))

class Element:
	properties = {}
	
	def __init__(self,name,elemtype="DmElement",id=None):
		if type(name) != str or type(elemtype) != str or (id and type(id) != uuid.UUID):
			raise TypeError("Expected str, [str, uuid.UUID]")
			
		self.name = name
		self.type = elemtype		
		self.id = id if id else uuid.uuid4()
		
		self.properties = {}
		self.property_order = []
		
	def __repr__(self):
		return "<Datamodel element \"{}\" ({})>".format(self.name,self.type)
		
	def add_property(self,name,value,prop_type = None):
		t = type(value)
		if self.properties.get(name):
			raise ValueError("Property \"{}\" already exists".format(name))
		array_types = [list,set,tuple,array.array]
		if t in array_types and not prop_type:
			raise ValueError("An array type must be specified")
		if t not in Property._dmxtype and t not in array_types:
			raise ValueError("Unsupported data type ({})".format(t))
			
		if t in array_types:
			if prop_type == Element: prop_type = _ElementArray
			elif prop_type == int: prop_type = _IntArray
			elif prop_type == float: prop_type = _FloatArray
			elif prop_type == bool: prop_type = _BoolArray
			elif prop_type == str: prop_type = _StrArray
			elif prop_type == Binary: prop_type = _BinaryArray
			elif prop_type == Time: prop_type = _TimeArray
			elif prop_type == Color: prop_type = _ColorArray
			elif prop_type == Vector2: prop_type = _Vector2Array
			elif prop_type == Vector3: prop_type = _Vector3Array
			elif prop_type == Vector4: prop_type = _Vector4Array
			elif prop_type == Angle: prop_type = _AngleArray
			elif prop_type == Quaternion: prop_type = _QuaternionArray
			elif prop_type == Matrix: prop_type = _MatrixArray
			else: raise ValueError("Unsupported array type")			
			value = prop_type(list(value))
		self.properties[name] = Property(name,value)
		self.property_order.append(name)

Property._dmxtype[1] = Element

class DataModel:
	_dmx_header = "<!-- dmx encoding {} {} format {} {} -->\n"
	elements = []
	root = None
	
	def __init__(self,encoding,encoding_ver,format,format_ver):
		if type(encoding) != str or type(encoding_ver) != int or type(format) != str or type(format_ver) != int:
			raise TypeError("Expected str, int, str, int")
			
		self.encoding = encoding
		self.encoding_ver = encoding_ver
		self.format = format
		self.format_ver = format_ver
		
		self.elements = []
		
	def add_element(self,name,elemtype="DmElement",id=None):
		elem = Element(name,elemtype,id)
		self.elements.append(elem)
		if len(self.elements) == 1: self.root = elem
		if type(elem) == Element: elem.datamodel = self
		if type(elem) == _ElementArray:
			for i in elem:
				i.datamodel = self
		return elem
		
	def find_element(self,name):
		for elem in self.elements:
			if elem.name == name:
				return elem				
		
	def remove_element(self,element):
		pass
		
	def _write(self,value = None, elem = None, use_str_dict = True):
		t = type(value)
		if t == bytes:
			self.out.write(value)
		
		elif t == uuid.UUID:
			self.out.write(value.bytes)
		elif t == Element:
			raise Error("Don't write elements as properites")
		elif t == str:
			self.out.write( _get_string(self,value,use_str_dict) )
				
		elif issubclass(t, _Array):
			self.out.write( struct.pack("i",len(value.list)) )
			self.out.write( value.tobytes(self,elem) )
		elif issubclass(t,_Vector):
			self.out.write(value.tobytes())
		
		elif t in [bool,chr]:
			self.out.write( struct.pack("b",value) )
		elif t == int:
			self.out.write( struct.pack("i",value) )
		elif t == float:
			self.out.write( struct.pack("f",value) )	
		else:
			self.out.write(_null)
	
	def _write_element_index(self,elem):
		self._write(elem.type)
		self._write(elem.name)
		self._write(elem.id)
		
		self.elem_chain.append(elem)
		
		self.elem_index.append(elem)
		for name in elem.property_order:
			prop = elem.properties[name]
			t = type(prop.value)
			if t == Element and prop.value not in self.elem_index:
				self._write_element_index(prop.value)
			if t == _ElementArray:
				for i in prop.value.list:
					if i not in self.elem_index:
						self._write_element_index(i)
		
	def _write_element_props(self,elem):
		elem = self.elem_chain[0]
		written_elems = [elem]
		self._write(len(elem.properties))
		for name in elem.property_order:
			prop = elem.properties[name]
			self._write(name)
			self._write(struct.pack("b",prop.typeid()))
			if type(prop.value) == Element:
				self._write(self.elem_index.index(prop.value),elem)
			else:
				self._write(prop.value,elem)
		del self.elem_chain[0]
		
		if len(self.elem_chain) == 0:
			return
		else:
			self._write_element_props(elem)			
		
		#for name in elem.property_order:
		#	prop = elem.properties[name]
		#	if prop.value not in written_elems:
		#		t = type(prop.value)
		#		if t == _ElementArray:
		#			for i in prop.value.list:
		#				self._write_element_props(i)
		#				written_elems.append(i)
		#	if prop.value not in written_elems:
		#		t = type(prop.value)
		#		if t == Element:
		#			self._write_element_props(prop.value)
		#			written_elems.append(prop.value)
		
	def _write_element(self,elem):
		self._write_element_index(elem)		
		self._write_element_props(elem)
		
	def _build_str_dict(self,elem):
		self.str_dict.add(elem.name)
		self.str_dict_checked.append(elem)
		self.str_dict.add(elem.type)
		for name in elem.property_order:
			prop = elem.properties[name]
			self.str_dict.add(name)
			if type(prop.value) == str:
				self.str_dict.add(prop.value)
			#if type(prop.value) == _StrArray:
			#	for i in prop.value.list:
			#		self.str_dict.add(i)
			if type(prop.value) == Element:
				if prop.value not in self.str_dict_checked:
					self._build_str_dict(prop.value)
			if type(prop.value) == _ElementArray:
				for i in prop.value.list:
					if i not in self.str_dict_checked:
						self._build_str_dict(i)				
		
	def write(self,path):
		self.out = open(path,'wb')
		self.str_dict = []
		self.str_dict_checked = []
		self.elem_index = []
		
		# header
		self._write(self._dmx_header.format(self.encoding,self.encoding_ver,self.format,self.format_ver))
		
		# string dictionary
		self.str_dict = set()
		self._build_str_dict(self.root)
		self.str_dict = list(self.str_dict)
		
		self._write(len(self.str_dict))
		x=0
		for i in self.str_dict:
			self._write(i,use_str_dict = False)
			print(x,i)
			x+=1
			
		# count elements
		out_elems = set()
		def _count_child_elems(elem):
			out_elems.add(elem)
			for name in elem.property_order:
				prop = elem.properties[name]
				t = type(prop.value)
				if prop.value not in out_elems:
					if t == Element:
						_count_child_elems(prop.value)
					if t == _ElementArray:
						for i in prop.value.list:
							_count_child_elems(i)
		_count_child_elems(self.root)
		self._write(len(out_elems))
		
		self.elem_chain = []
		self._write_element(self.root) # only write stuff referenced by the first element
				
		self.out.close()