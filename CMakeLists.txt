cmake_minimum_required(VERSION 3.15)
project(AutoMesh CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# nanoflann
FetchContent_Declare(
  nanoflann
  GIT_REPOSITORY https://github.com/jlblancoc/nanoflann.git
  GIT_TAG v1.5.0
)
FetchContent_MakeAvailable(nanoflann)

# Eigen
FetchContent_Declare(
  eigen
  GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
  GIT_TAG 3.4.0
)
FetchContent_MakeAvailable(eigen)

# tinygltf
FetchContent_Declare(
  tinygltf
  GIT_REPOSITORY https://github.com/syoyo/tinygltf.git
  GIT_TAG release
)
FetchContent_MakeAvailable(tinygltf)

# happly
FetchContent_Declare(
  happly
  GIT_REPOSITORY https://github.com/Alrecenk/happly.git
  GIT_TAG master
)
FetchContent_MakeAvailable(happly)

add_subdirectory(src)
