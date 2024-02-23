install_test_dependencies () {
    pip install ".[tests,docs]"
}

copy_test_files () {
    cp -r $CI_SOURCE_ROOT/tests $CI_TEST_ROOT/tests
    cp $CI_SOURCE_ROOT/pyproject.toml $CI_TEST_ROOT
}

get_os_arch () {
    uname_info=$(uname -a)

    rhel7=$(echo "$uname_info" | grep "el7")
    rhel8=$(echo "$uname_info" | grep "el8")

    os_arch="undetermined"

    if [ "$rhel7" ]; then
        os_arch="x86_64_RH_7"
    elif [ "$rhel8" ]; then
        os_arch="x86_64_RH_8"
    else
        echo "$os_arch"
        exit 1
    fi

    echo "$os_arch"
    exit 0
}

start_tests () {
    os_arch="$(get_os_arch)"
    pytest -n auto --flow-simulator="/project/res/$os_arch/bin/flowdaily" --eclipse-simulator="runeclipse"
}
