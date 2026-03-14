"""Tests for all language parsers (Go, Rust, Java, C#, Ruby, PHP, Swift, Kotlin, C/C++, Config, Web)."""

import pytest

from src.xray.parsers import get_parser_for_file, get_supported_extensions


# ------------------------------------------------------------------
# Parser Registry
# ------------------------------------------------------------------


class TestParserRegistry:
    """Verify parser auto-registration and supported extensions."""

    def test_supported_extension_count(self):
        exts = get_supported_extensions()
        assert len(exts) >= 40

    def test_python_registered(self):
        p = get_parser_for_file("test.py")
        assert p is not None
        assert p.language_name() == "python"

    def test_go_registered(self):
        p = get_parser_for_file("test.go")
        assert p is not None
        assert p.language_name() == "go"

    def test_rust_registered(self):
        p = get_parser_for_file("test.rs")
        assert p is not None
        assert p.language_name() == "rust"

    def test_java_registered(self):
        p = get_parser_for_file("test.java")
        assert p is not None
        assert p.language_name() == "java"

    def test_csharp_registered(self):
        p = get_parser_for_file("test.cs")
        assert p is not None
        assert p.language_name() == "csharp"

    def test_ruby_registered(self):
        p = get_parser_for_file("test.rb")
        assert p is not None
        assert p.language_name() == "ruby"

    def test_php_registered(self):
        p = get_parser_for_file("test.php")
        assert p is not None
        assert p.language_name() == "php"

    def test_swift_registered(self):
        p = get_parser_for_file("test.swift")
        assert p is not None
        assert p.language_name() == "swift"

    def test_kotlin_registered(self):
        p = get_parser_for_file("test.kt")
        assert p is not None
        assert p.language_name() == "kotlin"

    def test_c_registered(self):
        p = get_parser_for_file("test.c")
        assert p is not None
        assert p.language_name() == "c"

    def test_cpp_registered(self):
        p = get_parser_for_file("test.cpp")
        assert p is not None
        assert p.language_name() == "cpp"

    def test_html_registered(self):
        p = get_parser_for_file("test.html")
        assert p is not None
        assert p.language_name() == "html"

    def test_css_registered(self):
        p = get_parser_for_file("test.css")
        assert p is not None
        assert p.language_name() == "html"

    def test_config_json_registered(self):
        p = get_parser_for_file("test.json")
        assert p is not None
        assert p.language_name() == "config"

    def test_config_yaml_registered(self):
        p = get_parser_for_file("test.yaml")
        assert p is not None
        assert p.language_name() == "config"

    def test_unknown_extension(self):
        p = get_parser_for_file("test.xyz")
        assert p is None


# ------------------------------------------------------------------
# Go Parser
# ------------------------------------------------------------------

GO_SAMPLE = """\
package main

import "fmt"

type User struct {
    Name string
    Age  int
}

type Logger interface {
    Log(msg string)
}

func greet(name string) string {
    return "Hello, " + name
}

func (u *User) String() string {
    return u.Name
}
"""


class TestGoParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.go")
        self.entities, self.edges = self.parser.parse_file("test.go", GO_SAMPLE)

    def test_file_entity(self):
        files = [e for e in self.entities if e.type.value == "file"]
        assert len(files) == 1

    def test_function_extracted(self):
        funcs = [e for e in self.entities if e.type.value == "function"]
        names = {e.name for e in funcs}
        assert "greet" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "String" in names

    def test_struct_extracted(self):
        structs = [e for e in self.entities if e.type.value == "struct"]
        names = {e.name for e in structs}
        assert "User" in names

    def test_interface_extracted(self):
        ifaces = [e for e in self.entities if e.type.value == "interface"]
        names = {e.name for e in ifaces}
        assert "Logger" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1
        names = {e.qualified_name for e in imports}
        assert "fmt" in names

    def test_edges_created(self):
        assert len(self.edges) > 0


# ------------------------------------------------------------------
# Rust Parser
# ------------------------------------------------------------------

RUST_SAMPLE = """\
use std::fmt;

struct User {
    name: String,
    age: u32,
}

trait Logger {
    fn log(&self, msg: &str);
}

impl Logger for User {
    fn log(&self, msg: &str) {
        println!("{}", msg);
    }
}

fn greet(name: &str) -> String {
    format!("Hello, {}", name)
}

enum Color {
    Red,
    Green,
    Blue,
}
"""


class TestRustParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.rs")
        self.entities, self.edges = self.parser.parse_file("test.rs", RUST_SAMPLE)

    def test_function_extracted(self):
        funcs = [e for e in self.entities if e.type.value == "function"]
        names = {e.name for e in funcs}
        assert "greet" in names

    def test_struct_extracted(self):
        structs = [e for e in self.entities if e.type.value == "struct"]
        names = {e.name for e in structs}
        assert "User" in names

    def test_trait_extracted(self):
        traits = [e for e in self.entities if e.type.value == "trait"]
        names = {e.name for e in traits}
        assert "Logger" in names

    def test_enum_extracted(self):
        enums = [e for e in self.entities if e.type.value == "enum"]
        names = {e.name for e in enums}
        assert "Color" in names

    def test_impl_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "log" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1


# ------------------------------------------------------------------
# Java Parser
# ------------------------------------------------------------------

JAVA_SAMPLE = """\
package com.example;

import java.util.List;

public class User {
    private String name;

    public User(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}

interface Logger {
    void log(String msg);
}

enum Color {
    RED, GREEN, BLUE
}
"""


class TestJavaParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.java")
        self.entities, self.edges = self.parser.parse_file("test.java", JAVA_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_interface_extracted(self):
        ifaces = [e for e in self.entities if e.type.value == "interface"]
        names = {e.name for e in ifaces}
        assert "Logger" in names

    def test_enum_extracted(self):
        enums = [e for e in self.entities if e.type.value == "enum"]
        names = {e.name for e in enums}
        assert "Color" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "getName" in names

    def test_constructor_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "User" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1


# ------------------------------------------------------------------
# C# Parser
# ------------------------------------------------------------------

CSHARP_SAMPLE = """\
using System;
using System.Collections.Generic;

namespace MyApp {
    public class User {
        public string GetName() {
            return "test";
        }
    }

    interface ILogger {
        void Log(string msg);
    }

    enum Color {
        Red, Green, Blue
    }
}
"""


class TestCSharpParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.cs")
        self.entities, self.edges = self.parser.parse_file("test.cs", CSHARP_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "GetName" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 2


# ------------------------------------------------------------------
# Ruby Parser
# ------------------------------------------------------------------

RUBY_SAMPLE = """\
require 'json'
require_relative 'helper'

class User < Base
  MAX_AGE = 150

  def initialize(name)
    @name = name
  end

  def greet(msg)
    puts msg
  end
end

module Logging
  def log(msg)
    puts msg
  end
end
"""


class TestRubyParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.rb")
        self.entities, self.edges = self.parser.parse_file("test.rb", RUBY_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_module_extracted(self):
        modules = [e for e in self.entities if e.type.value == "module"]
        names = {e.name for e in modules}
        assert "Logging" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "greet" in names
        assert "initialize" in names

    def test_inheritance(self):
        inherits = [e for e in self.edges if e.relation.value == "inherits"]
        assert len(inherits) >= 1


# ------------------------------------------------------------------
# PHP Parser
# ------------------------------------------------------------------

PHP_SAMPLE = """\
<?php
namespace App\\Models;

use App\\Contracts\\Loggable;

class User {
    public function getName(): string {
        return $this->name;
    }

    public function setName(string $name): void {
        $this->name = $name;
    }
}

interface Loggable {
    public function log(string $msg): void;
}
"""


class TestPHPParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.php")
        self.entities, self.edges = self.parser.parse_file("test.php", PHP_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "getName" in names

    def test_interface_extracted(self):
        ifaces = [e for e in self.entities if e.type.value == "interface"]
        names = {e.name for e in ifaces}
        assert "Loggable" in names


# ------------------------------------------------------------------
# Swift Parser
# ------------------------------------------------------------------

SWIFT_SAMPLE = """\
import Foundation

class User {
    func greet() {
        print("hello")
    }
}

struct Point {
    func distance() -> Double {
        return 0.0
    }
}

enum Color {
    case red
    case green
}

protocol Loggable {
    func log()
}
"""


class TestSwiftParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.swift")
        self.entities, self.edges = self.parser.parse_file("test.swift", SWIFT_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_struct_extracted(self):
        structs = [e for e in self.entities if e.type.value == "struct"]
        names = {e.name for e in structs}
        assert "Point" in names

    def test_enum_extracted(self):
        enums = [e for e in self.entities if e.type.value == "enum"]
        names = {e.name for e in enums}
        assert "Color" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1


# ------------------------------------------------------------------
# Kotlin Parser
# ------------------------------------------------------------------

KOTLIN_SAMPLE = """\
import kotlin.collections.List

class User {
    fun greet() {
        println("hello")
    }
}

object Singleton {
    fun instance() { }
}
"""


class TestKotlinParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.kt")
        self.entities, self.edges = self.parser.parse_file("test.kt", KOTLIN_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "User" in names

    def test_method_extracted(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "greet" in names

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1


# ------------------------------------------------------------------
# C Parser
# ------------------------------------------------------------------

C_SAMPLE = """\
#include <stdio.h>
#include "myheader.h"

struct Point {
    int x;
    int y;
};

enum Color {
    RED,
    GREEN,
    BLUE
};

void greet(const char* name) {
    printf("Hello, %s\\n", name);
}

int add(int a, int b) {
    return a + b;
}
"""


class TestCParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.c")
        self.entities, self.edges = self.parser.parse_file("test.c", C_SAMPLE)

    def test_function_extracted(self):
        funcs = [e for e in self.entities if e.type.value == "function"]
        names = {e.name for e in funcs}
        assert "greet" in names
        assert "add" in names

    def test_struct_extracted(self):
        structs = [e for e in self.entities if e.type.value == "struct"]
        names = {e.name for e in structs}
        assert "Point" in names

    def test_enum_extracted(self):
        enums = [e for e in self.entities if e.type.value == "enum"]
        names = {e.name for e in enums}
        assert "Color" in names

    def test_include_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 2


# ------------------------------------------------------------------
# C++ Parser
# ------------------------------------------------------------------

CPP_SAMPLE = """\
#include <string>
#include <vector>

class Animal {
    void speak() { }
};

class Dog {
    void bark() { }
};

struct Point {
    int x;
    int y;
};

void greet(const std::string& name) {
    // greet
}
"""


class TestCppParser:
    def setup_method(self):
        self.parser = get_parser_for_file("test.cpp")
        self.entities, self.edges = self.parser.parse_file("test.cpp", CPP_SAMPLE)

    def test_class_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "Animal" in names
        assert "Dog" in names

    def test_function_extracted(self):
        funcs = [e for e in self.entities if e.type.value == "function"]
        names = {e.name for e in funcs}
        assert "greet" in names

    def test_struct_extracted(self):
        structs = [e for e in self.entities if e.type.value == "struct"]
        names = {e.name for e in structs}
        assert "Point" in names

    def test_include_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 2


# ------------------------------------------------------------------
# Config Parser
# ------------------------------------------------------------------

JSON_SAMPLE = '{"name": "blueprint", "version": "1.0", "database": {"host": "localhost"}}'
YAML_SAMPLE = """\
name: blueprint
version: "1.0"
database:
  host: localhost
"""
ENV_SAMPLE = """\
DATABASE_URL=postgres://localhost/db
API_KEY=secret123
DEBUG=true
"""
TOML_SAMPLE = """\
[project]
name = "blueprint"
version = "1.0"

[database]
host = "localhost"
"""


class TestConfigParser:
    def test_json_parsing(self):
        parser = get_parser_for_file("test.json")
        entities, edges = parser.parse_file("config.json", JSON_SAMPLE)
        names = {e.name for e in entities}
        assert "name" in names
        assert "database" in names

    def test_yaml_parsing(self):
        parser = get_parser_for_file("test.yaml")
        entities, edges = parser.parse_file("config.yaml", YAML_SAMPLE)
        names = {e.name for e in entities}
        assert "name" in names
        assert "database" in names

    def test_env_parsing(self):
        parser = get_parser_for_file("test.env")
        entities, edges = parser.parse_file("project.env", ENV_SAMPLE)
        names = {e.name for e in entities}
        assert "DATABASE_URL" in names
        assert "API_KEY" in names

    def test_toml_parsing(self):
        parser = get_parser_for_file("test.toml")
        entities, edges = parser.parse_file("config.toml", TOML_SAMPLE)
        names = {e.name for e in entities}
        assert "project" in names or "name" in names

    def test_env_constants(self):
        parser = get_parser_for_file("test.env")
        entities, edges = parser.parse_file("project.env", ENV_SAMPLE)
        constants = [e for e in entities if e.type.value == "constant"]
        assert len(constants) >= 2


# ------------------------------------------------------------------
# Web Parser
# ------------------------------------------------------------------

HTML_SAMPLE = """\
<!DOCTYPE html>
<html>
<head>
    <link href="styles.css" rel="stylesheet">
    <script src="app.js"></script>
</head>
<body>
    <div id="main" class="container">
        <form action="/api/login" method="POST">
            <input type="text">
        </form>
        <a href="https://example.com">Link</a>
    </div>
</body>
</html>
"""

CSS_SAMPLE = """\
@import "base.css";

:root {
    --primary-color: #333;
    --bg-color: white;
}

.container {
    max-width: 1200px;
}

#main {
    display: flex;
}

@media (max-width: 768px) {
    .container {
        max-width: 100%;
    }
}
"""


class TestWebParser:
    def test_html_script_imports(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        imports = [e for e in entities if e.type.value == "import"]
        names = {e.name for e in imports}
        assert "app.js" in names

    def test_html_link_imports(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        imports = [e for e in entities if e.type.value == "import"]
        names = {e.name for e in imports}
        assert "styles.css" in names

    def test_html_form_endpoint(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        endpoints = [e for e in entities if e.type.value == "endpoint"]
        assert len(endpoints) >= 1
        names = {e.name for e in endpoints}
        assert "/api/login" in names

    def test_html_id_extraction(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        vars = [e for e in entities if e.type.value == "variable"]
        names = {e.name for e in vars}
        assert "#main" in names

    def test_css_import(self):
        parser = get_parser_for_file("test.css")
        entities, edges = parser.parse_file("style.css", CSS_SAMPLE)
        imports = [e for e in entities if e.type.value == "import"]
        names = {e.name for e in imports}
        assert "base.css" in names

    def test_css_selectors(self):
        parser = get_parser_for_file("test.css")
        entities, edges = parser.parse_file("style.css", CSS_SAMPLE)
        vars = [e for e in entities if e.type.value == "variable"]
        names = {e.name for e in vars}
        assert ".container" in names or any(".container" in n for n in names)

    def test_css_custom_properties(self):
        parser = get_parser_for_file("test.css")
        entities, edges = parser.parse_file("style.css", CSS_SAMPLE)
        vars = [e for e in entities if e.type.value == "variable"]
        names = {e.name for e in vars}
        assert "--primary-color" in names


# ==================================================================
# Deeper coverage: edges, signatures, metrics, empty inputs
# ==================================================================


class TestGoParserDeep:
    """Deeper Go parser tests: edges, signatures, metrics, edge cases."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.go")
        self.entities, self.edges = self.parser.parse_file("test.go", GO_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4  # struct, interface, func, method

    def test_imports_edges(self):
        imports_edges = [e for e in self.edges if e.relation.value == "imports"]
        assert len(imports_edges) >= 1

    def test_function_signature(self):
        funcs = [e for e in self.entities if e.name == "greet"]
        assert len(funcs) == 1
        assert "func greet" in funcs[0].signature

    def test_method_qualified_name(self):
        methods = [e for e in self.entities if e.name == "String"]
        assert len(methods) == 1
        assert "User.String" in methods[0].qualified_name

    def test_function_has_metrics(self):
        funcs = [e for e in self.entities if e.name == "greet"]
        assert funcs[0].metrics is not None
        assert funcs[0].metrics.loc_total >= 1

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.go", "")
        assert len(entities) <= 1  # at most a file entity

    def test_symbols_off(self):
        entities, edges = self.parser.parse_file("test.go", GO_SAMPLE, extract_symbols=False)
        assert len(entities) == 1  # file entity only
        assert entities[0].type.value == "file"

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "go"

    def test_all_entities_have_location(self):
        for e in self.entities:
            assert e.location is not None
            assert e.location.file == "test.go"


class TestRustParserDeep:
    """Deeper Rust parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.rs")
        self.entities, self.edges = self.parser.parse_file("test.rs", RUST_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4

    def test_function_signature(self):
        funcs = [e for e in self.entities if e.name == "greet"]
        assert len(funcs) == 1
        assert "fn greet" in funcs[0].signature

    def test_struct_signature(self):
        structs = [e for e in self.entities if e.name == "User" and e.type.value == "struct"]
        assert len(structs) == 1
        assert "struct User" in structs[0].signature

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.rs", "")
        assert len(entities) <= 1  # at most a file entity

    def test_symbols_off(self):
        entities, edges = self.parser.parse_file("test.rs", RUST_SAMPLE, extract_symbols=False)
        assert len(entities) == 1
        assert entities[0].type.value == "file"

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "rust"


class TestJavaParserDeep:
    """Deeper Java parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.java")
        self.entities, self.edges = self.parser.parse_file("test.java", JAVA_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4

    def test_imports_edges(self):
        imports_edges = [e for e in self.edges if e.relation.value == "imports"]
        assert len(imports_edges) >= 1

    def test_class_signature(self):
        classes = [e for e in self.entities if e.name == "User" and e.type.value == "class"]
        assert len(classes) == 1
        assert "class User" in classes[0].signature

    def test_method_has_metrics(self):
        methods = [e for e in self.entities if e.name == "getName"]
        assert len(methods) == 1
        assert methods[0].metrics is not None

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.java", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "java"


class TestCSharpParserDeep:
    """Deeper C# parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.cs")
        self.entities, self.edges = self.parser.parse_file("test.cs", CSHARP_SAMPLE)

    def test_interface_extracted(self):
        ifaces = [e for e in self.entities if e.type.value == "interface"]
        names = {e.name for e in ifaces}
        assert "ILogger" in names

    def test_enum_extracted(self):
        enums = [e for e in self.entities if e.type.value == "enum"]
        names = {e.name for e in enums}
        assert "Color" in names

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 3

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.cs", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "csharp"


class TestRubyParserDeep:
    """Deeper Ruby parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.rb")
        self.entities, self.edges = self.parser.parse_file("test.rb", RUBY_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        names = {e.name for e in imports}
        assert "json" in names
        assert "helper" in names

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.rb", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "ruby"


class TestPHPParserDeep:
    """Deeper PHP parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.php")
        self.entities, self.edges = self.parser.parse_file("test.php", PHP_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 3

    def test_import_extracted(self):
        imports = [e for e in self.entities if e.type.value == "import"]
        assert len(imports) >= 1

    def test_multiple_methods(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "getName" in names
        assert "setName" in names

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.php", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "php"


class TestSwiftParserDeep:
    """Deeper Swift parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.swift")
        self.entities, self.edges = self.parser.parse_file("test.swift", SWIFT_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 5  # class, struct, enum, protocol, methods, import

    def test_protocol_extracted(self):
        ifaces = [e for e in self.entities if e.type.value == "interface"]
        names = {e.name for e in ifaces}
        assert "Loggable" in names

    def test_method_inside_class(self):
        methods = [e for e in self.entities if e.type.value == "method"]
        names = {e.name for e in methods}
        assert "greet" in names

    def test_struct_signature(self):
        structs = [e for e in self.entities if e.name == "Point"]
        assert len(structs) == 1
        assert "struct Point" in structs[0].signature

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.swift", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "swift"


class TestKotlinParserDeep:
    """Deeper Kotlin parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.kt")
        self.entities, self.edges = self.parser.parse_file("test.kt", KOTLIN_SAMPLE)

    def test_object_extracted(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "Singleton" in names

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 3

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.kt", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "kotlin"


class TestCParserDeep:
    """Deeper C parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.c")
        self.entities, self.edges = self.parser.parse_file("test.c", C_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4

    def test_function_has_metrics(self):
        funcs = [e for e in self.entities if e.name == "add"]
        assert len(funcs) == 1
        assert funcs[0].metrics is not None

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.c", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "c"


class TestCppParserDeep:
    """Deeper C++ parser tests."""

    def setup_method(self):
        self.parser = get_parser_for_file("test.cpp")
        self.entities, self.edges = self.parser.parse_file("test.cpp", CPP_SAMPLE)

    def test_contains_edges(self):
        contains = [e for e in self.edges if e.relation.value == "contains"]
        assert len(contains) >= 4

    def test_multiple_classes(self):
        classes = [e for e in self.entities if e.type.value == "class"]
        names = {e.name for e in classes}
        assert "Animal" in names
        assert "Dog" in names

    def test_empty_source(self):
        entities, edges = self.parser.parse_file("empty.cpp", "")
        assert len(entities) <= 1  # at most a file entity

    def test_all_entities_have_language(self):
        for e in self.entities:
            assert e.language == "cpp"


class TestConfigParserDeep:
    """Deeper config parser tests."""

    def test_json_file_entity(self):
        parser = get_parser_for_file("test.json")
        entities, edges = parser.parse_file("config.json", JSON_SAMPLE)
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1

    def test_json_nested_keys(self):
        parser = get_parser_for_file("test.json")
        entities, edges = parser.parse_file("config.json", JSON_SAMPLE)
        names = {e.name for e in entities}
        assert "host" in names

    def test_yaml_file_entity(self):
        parser = get_parser_for_file("test.yaml")
        entities, edges = parser.parse_file("config.yaml", YAML_SAMPLE)
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1

    def test_empty_json(self):
        parser = get_parser_for_file("test.json")
        entities, edges = parser.parse_file("empty.json", "{}")
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1

    def test_empty_yaml(self):
        parser = get_parser_for_file("test.yaml")
        entities, edges = parser.parse_file("empty.yaml", "")
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1


class TestWebParserDeep:
    """Deeper web parser tests."""

    def test_html_file_entity(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1

    def test_html_contains_edges(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("index.html", HTML_SAMPLE)
        contains = [e for e in edges if e.relation.value == "contains"]
        assert len(contains) >= 2

    def test_css_file_entity(self):
        parser = get_parser_for_file("test.css")
        entities, edges = parser.parse_file("style.css", CSS_SAMPLE)
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1

    def test_empty_html(self):
        parser = get_parser_for_file("test.html")
        entities, edges = parser.parse_file("empty.html", "")
        files = [e for e in entities if e.type.value == "file"]
        assert len(files) == 1
