install_test_dependencies () {
  pip install -r test_requirements.txt
  pip install -r docs_requirements.txt
}

copy_test_files () {
    cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT/tests
    cp $CI_SOURCE_ROOT/setup.cfg $CI_TEST_ROOT
}

start_tests () {
    pytest --flow-simulator="/project/res/x86_64_RH_7/bin/flowdaily" --eclipse-simulator="runeclipse"
}
