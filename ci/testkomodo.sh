install_test_dependencies () {
    pip install ".[tests,docs]"
}

copy_test_files () {
    cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT/tests
    cp $CI_SOURCE_ROOT/pyproject.toml $CI_TEST_ROOT
}

start_tests () {
    pytest -n auto --flow-simulator="/project/res/x86_64_RH_7/bin/flowdaily" --eclipse-simulator="runeclipse"
}
