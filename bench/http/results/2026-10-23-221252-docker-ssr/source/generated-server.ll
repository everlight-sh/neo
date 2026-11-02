target triple = "aarch64-unknown-linux-gnu"

%ax_arr = type { ptr, i64, i64 }

@ax_runtime_state = internal global [256 x i64] zeroinitializer, align 16
declare double @llvm.sqrt.f64(double)
declare void @llvm.assume(i1)
declare <16 x double> @llvm.sqrt.v16f64(<16 x double>)
declare i1 @llvm.vector.reduce.or.v16i1(<16 x i1>)
declare i64 @llvm.vector.reduce.add.v16i64(<16 x i64>)
declare double @llvm.vector.reduce.fadd.v16f64(double, <16 x double>)
declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1)
declare i64 @llvm.ctlz.i64(i64, i1)

@.str.1 = private unnamed_addr constant [55 x i8] c"check failed: ((offset >= 0) && (offset <= n)) at 67:5\00"
@.str.2 = private unnamed_addr constant [78 x i8] c"check failed: ((header_bytes >= 0) && (header_bytes <= (n - offset))) at 73:7\00"
@.str.3 = private unnamed_addr constant [50 x i8] c"check failed: ((n >= 0) && (n <= 65536)) at 104:5\00"
@.str.4 = private unnamed_addr constant [5 x i8] c"port\00"
@.str.5 = private unnamed_addr constant [11 x i8] c"(port > 0)\00"
@.str.6 = private unnamed_addr constant [15 x i8] c"(port < 65536)\00"
@.bytes.1 = private unnamed_addr constant [12 x i8] c"axon: trap: "
@.bytes.2 = private unnamed_addr constant [1 x i8] c"\0A"
@.bytes.3 = private unnamed_addr constant [12 x i8] c"mmap failed\00"
@.bytes.4 = private unnamed_addr constant [29 x i8] c"allocation size out of range\00"
@.bytes.5 = private unnamed_addr constant [16 x i8] c"calloc overflow\00"
@.bytes.6 = private unnamed_addr constant [15 x i8] c"axon: argument "
@.bytes.7 = private unnamed_addr constant [18 x i8] c": not an integer: "
@.bytes.8 = private unnamed_addr constant [13 x i8] c"AXON_THREADS\00"
@.bytes.9 = private unnamed_addr constant [23 x i8] c"parallel worker failed\00"
@.bytes.10 = private unnamed_addr constant [7 x i8] c"usage: "
@.bytes.11 = private unnamed_addr constant [1 x i8] c" "
@.bytes.12 = private unnamed_addr constant [27 x i8] c"axon: precondition failed: "
@.bytes.13 = private unnamed_addr constant [4 x i8] c"nan\0A"
@.bytes.14 = private unnamed_addr constant [3 x i8] c"-0\0A"
@.bytes.15 = private unnamed_addr constant [2 x i8] c"0\0A"
@.bytes.16 = private unnamed_addr constant [5 x i8] c"-inf\0A"
@.bytes.17 = private unnamed_addr constant [4 x i8] c"inf\0A"
@.bytes.18 = private unnamed_addr constant [14 x i8] c"socket failed\00"
@.bytes.19 = private unnamed_addr constant [19 x i8] c"bind/listen failed\00"
@.bytes.20 = private unnamed_addr constant [15 x i8] c"content-length:"
@.bytes.21 = private unnamed_addr constant [18 x i8] c"transfer-encoding:"
@.bytes.22 = private unnamed_addr constant [11 x i8] c"connection:"
@.bytes.23 = private unnamed_addr constant [4 x i8] c"\0D\0A\0D\0A"
@.bytes.24 = private unnamed_addr constant [5 x i8] c"close"
@.bytes.25 = private unnamed_addr constant [8 x i8] c"HTTP/1.0"
@.bytes.26 = private unnamed_addr constant [10 x i8] c"keep-alive"
@.bytes.27 = private unnamed_addr constant [20 x i8] c"poll syscall failed\00"
@.bytes.28 = private unnamed_addr constant [38 x i8] c"worker notification socketpair failed\00"
@.bytes.29 = private unnamed_addr constant [24 x i8] c"HTTP worker fork failed\00"
@.bytes.30 = private unnamed_addr constant [23 x i8] c"axon: serving, workers="
@.bytes.31 = private unnamed_addr constant [25 x i8] c"epoll_ctl syscall failed\00"
@.bytes.32 = private unnamed_addr constant [29 x i8] c"epoll_create1 syscall failed\00"
@.bytes.33 = private unnamed_addr constant [27 x i8] c"epoll_pwait syscall failed\00"
@.bytes.34 = private unnamed_addr constant [20 x i8] c"invalid epoll token\00"
@.bytes.35 = private unnamed_addr constant [15 x i8] c"AXON_HTTP_POLL\00"
@.bytes.36 = private unnamed_addr constant [5 x i8] c"&amp;"
@.bytes.37 = private unnamed_addr constant [4 x i8] c"&lt;"
@.bytes.38 = private unnamed_addr constant [4 x i8] c"&gt;"
@.bytes.39 = private unnamed_addr constant [6 x i8] c"&quot;"
@.bytes.40 = private unnamed_addr constant [6 x i8] c"&#x27;"
@.bytes.41 = private unnamed_addr constant [20 x i8] c"<span class=\22badge\22>"
@.bytes.42 = private unnamed_addr constant [7 x i8] c"</span>"
@.bytes.43 = private unnamed_addr constant [29 x i8] c"<article class=\22card\22 title=\22"
@.bytes.44 = private unnamed_addr constant [6 x i8] c"\22><h2>"
@.bytes.45 = private unnamed_addr constant [10 x i8] c"</h2><div>"
@.bytes.46 = private unnamed_addr constant [16 x i8] c"</div></article>"
@.bytes.47 = private unnamed_addr constant [116 x i8] c"<html lang=\22en\22><head><title>JSX on Axon</title></head><body><main><h1>JSX on Axon</h1><article class=\22card\22 title=\22"
@.bytes.48 = private unnamed_addr constant [20 x i8] c"</h2><div><p>Hello, "
@.bytes.49 = private unnamed_addr constant [20 x i8] c"!</p><p data-count=\22"
@.bytes.50 = private unnamed_addr constant [12 x i8] c"\22>Requests: "
@.bytes.51 = private unnamed_addr constant [4 x i8] c"</p>"
@.bytes.52 = private unnamed_addr constant [53 x i8] c"<span class=\22badge\22>Featured &amp; independent</span>"
@.bytes.53 = private unnamed_addr constant [0 x i8] c""
@.bytes.54 = private unnamed_addr constant [3 x i8] c"<p>"
@.bytes.55 = private unnamed_addr constant [8 x i8] c"One item"
@.bytes.56 = private unnamed_addr constant [10 x i8] c"Many items"
@.bytes.57 = private unnamed_addr constant [136 x i8] c"</p><p>Compiled components &amp; escaped props.</p></div></article></main><footer>No browser JavaScript required.</footer></body></html>"
@.bytes.58 = private unnamed_addr constant [42 x i8] c"<script>alert(\22x\22)</script> & ' caf\C3\A9 \F0\9F\9A\80"
@.bytes.59 = private unnamed_addr constant [33 x i8] c"Axon & React's \22JSX\22 <components>"
@.bytes.60 = private unnamed_addr constant [15 x i8] c"<!DOCTYPE html>"
@.bytes.61 = private unnamed_addr constant [73 x i8] c"HTTP/1.1 200 OK\0D\0AContent-Type: text/html; charset=utf-8\0D\0AContent-Length: "
@.bytes.62 = private unnamed_addr constant [6 x i8] c"GET / "
@.bytes.63 = private unnamed_addr constant [6 x i8] c"GET /?"
@.bytes.64 = private unnamed_addr constant [10 x i8] c"GET /page/"
@.bytes.65 = private unnamed_addr constant [104 x i8] c"HTTP/1.1 400 Bad Request\0D\0AContent-Type: text/plain\0D\0AContent-Length: 30\0D\0A\0D\0Ausage: /page/N, 1 <= N <= 1000"
@.bytes.66 = private unnamed_addr constant [4 x i8] c"GET "
@.bytes.67 = private unnamed_addr constant [80 x i8] c"HTTP/1.1 404 Not Found\0D\0AContent-Type: text/plain\0D\0AContent-Length: 9\0D\0A\0D\0ANot Found"
@.bytes.68 = private unnamed_addr constant [54 x i8] c"HTTP/1.1 405 Method Not Allowed\0D\0AContent-Length: 0\0D\0A\0D\0A"
; ax_runtime_init  graph:74a6c9bb4137d629
define void @ax_runtime_init(ptr %p_envp) "no-builtins" {
entry:
  %a1 = alloca ptr
  store ptr %p_envp, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = getelementptr i8, ptr @ax_runtime_state, i64 0
  store ptr %t2, ptr %t3, align 1
  ret void
}

; rt_errno  graph:6f690fc95636d7d5
define internal ptr @ax_rt_errno__seq() "no-builtins" {
entry:
  %t1 = getelementptr i8, ptr @ax_runtime_state, i64 8
  ret ptr %t1
}

; rt_result  graph:a5836c12e556588e
define internal i64 @ax_rt_result__seq(i64 %p_value) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca i64
  %a13 = alloca i8
  store i64 %p_value, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = icmp slt i64 %t2, 0
  br i1 %t3, label %then5, label %else6
then5:
  %t8 = call ptr @ax_rt_errno__seq()
  %t9 = load i64, ptr %a1
  %t10 = sub i64 0, %t9
  %t11 = trunc i64 %t10 to i32
  %t12 = getelementptr i8, ptr %t8, i64 0
  store i32 %t11, ptr %t12, align 1
  store i8 0, ptr %a13
  store i64 -1, ptr %a4
  br label %join7
else6:
  %t14 = load i64, ptr %a1
  store i64 %t14, ptr %a4
  br label %join7
join7:
  %t15 = load i64, ptr %a4
  ret i64 %t15
}

; rt_cstrlen  graph:f3410de3ed0aadd1
define internal i64 @ax_rt_cstrlen__seq(ptr %p_text) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  store ptr %p_text, ptr %a1
  store i64 0, ptr %a2
  br label %loop_cond3
loop_cond3:
  %t6 = load ptr, ptr %a1
  %t7 = load i64, ptr %a2
  %t8 = getelementptr i8, ptr %t6, i64 %t7
  %t9 = load volatile i8, ptr %t8, align 1
  %t10 = trunc i64 0 to i8
  %t11 = icmp ne i8 %t9, %t10
  br i1 %t11, label %loop_body4, label %loop_exit5
loop_body4:
  %t12 = load i64, ptr %a2
  %t13 = add i64 %t12, 1
  store i64 %t13, ptr %a2
  br label %loop_cond3
loop_exit5:
  %t14 = load i64, ptr %a2
  ret i64 %t14
}

; rt_write_all  graph:861a6fe25a2699e9
define internal void @ax_rt_write_all__seq(i64 %p_fd, ptr %p_text, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca i64
  %a4 = alloca i64
  %a10 = alloca i1
  %a25 = alloca i64
  %a28 = alloca i64
  %a37 = alloca i1
  %a46 = alloca i64
  %a54 = alloca i64
  store i64 %p_fd, ptr %a1
  store ptr %p_text, ptr %a2
  store i64 %p_n, ptr %a3
  store i64 0, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load i64, ptr %a4
  %t9 = icmp sge i64 %t8, 0
  store i1 %t9, ptr %a10
  br i1 %t9, label %rhs11, label %join12
rhs11:
  %t13 = load i64, ptr %a4
  %t14 = load i64, ptr %a3
  %t15 = icmp slt i64 %t13, %t14
  store i1 %t15, ptr %a10
  br label %join12
join12:
  %t16 = load i1, ptr %a10
  br i1 %t16, label %loop_body6, label %loop_exit7
loop_body6:
  %t17 = load i64, ptr %a1
  %t18 = load ptr, ptr %a2
  %t19 = load i64, ptr %a4
  %t20 = getelementptr i8, ptr %t18, i64 %t19
  %t21 = load i64, ptr %a3
  %t22 = load i64, ptr %a4
  %t23 = sub i64 %t21, %t22
  %t24 = call i64 @ax_rt_write__seq(i64 %t17, ptr %t20, i64 %t23)
  store i64 %t24, ptr %a25
  %t26 = load i64, ptr %a25
  %t27 = icmp sgt i64 %t26, 0
  br i1 %t27, label %then29, label %else30
then29:
  %t32 = load i64, ptr %a4
  %t33 = load i64, ptr %a25
  %t34 = add i64 %t32, %t33
  store i64 %t34, ptr %a28
  br label %join31
else30:
  %t35 = load i64, ptr %a25
  %t36 = icmp slt i64 %t35, 0
  store i1 %t36, ptr %a37
  br i1 %t36, label %rhs38, label %join39
rhs38:
  %t40 = call ptr @ax_rt_errno__seq()
  %t41 = getelementptr i8, ptr %t40, i64 0
  %t42 = load i32, ptr %t41, align 1
  %t43 = trunc i64 4 to i32
  %t44 = icmp eq i32 %t42, %t43
  store i1 %t44, ptr %a37
  br label %join39
join39:
  %t45 = load i1, ptr %a37
  br i1 %t45, label %then47, label %else48
then47:
  %t50 = load i64, ptr %a4
  store i64 %t50, ptr %a46
  br label %join49
else48:
  store i64 -1, ptr %a46
  br label %join49
join49:
  %t51 = load i64, ptr %a46
  store i64 %t51, ptr %a28
  br label %join31
join31:
  %t52 = load i64, ptr %a28
  store i64 %t52, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t53 = load i64, ptr %a4
  store i64 %t53, ptr %a54
  ret void
}

; rt_puts  graph:871fbe81e6225e49
define internal void @ax_rt_puts__seq(i64 %p_fd, ptr %p_text) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  store i64 %p_fd, ptr %a1
  store ptr %p_text, ptr %a2
  %t3 = load i64, ptr %a1
  %t4 = load ptr, ptr %a2
  %t5 = load ptr, ptr %a2
  %t6 = call i64 @ax_rt_cstrlen__seq(ptr %t5)
  call void @ax_rt_write_all__seq(i64 %t3, ptr %t4, i64 %t6)
  ret void
}

; ax_trap  graph:adb26c764d45feed
define void @ax_trap(ptr %p_message) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a6 = alloca i8
  %a8 = alloca i8
  %a13 = alloca i8
  store ptr %p_message, ptr %a1
  %t2 = insertvalue %ax_arr undef, ptr @.bytes.1, 0
  %t3 = insertvalue %ax_arr %t2, i64 12, 1
  %t4 = insertvalue %ax_arr %t3, i64 0, 2
  %t5 = extractvalue %ax_arr %t4, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t5, i64 12)
  store i8 0, ptr %a6
  %t7 = load ptr, ptr %a1
  call void @ax_rt_puts__seq(i64 2, ptr %t7)
  store i8 0, ptr %a8
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.2, 0
  %t10 = insertvalue %ax_arr %t9, i64 1, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = extractvalue %ax_arr %t11, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t12, i64 1)
  store i8 0, ptr %a13
  call void @ax_exit(i64 1)
  ret void
}

; memcpy  graph:1ec7eae04fc67cd2
define ptr @memcpy(ptr %p_dst, ptr %p_src, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a3 = alloca i64
  %a4 = alloca i64
  %a19 = alloca i8
  %a23 = alloca i64
  %a25 = alloca i64
  %a39 = alloca i8
  %a43 = alloca i64
  store ptr %p_dst, ptr %a1
  store ptr %p_src, ptr %a2
  store i64 %p_n, ptr %a3
  store i64 0, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load i64, ptr %a4
  %t9 = add i64 %t8, 8
  %t10 = load i64, ptr %a3
  %t11 = icmp sle i64 %t9, %t10
  br i1 %t11, label %loop_body6, label %loop_exit7
loop_body6:
  %t12 = load ptr, ptr %a1
  %t13 = load i64, ptr %a4
  %t14 = load ptr, ptr %a2
  %t15 = load i64, ptr %a4
  %t16 = getelementptr i8, ptr %t14, i64 %t15
  %t17 = load volatile i64, ptr %t16, align 1
  %t18 = getelementptr i8, ptr %t12, i64 %t13
  store volatile i64 %t17, ptr %t18, align 1
  store i8 0, ptr %a19
  %t20 = load i64, ptr %a4
  %t21 = add i64 %t20, 8
  store i64 %t21, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t22 = load i64, ptr %a4
  store i64 %t22, ptr %a23
  %t24 = load i64, ptr %a23
  store i64 %t24, ptr %a25
  br label %loop_cond26
loop_cond26:
  %t29 = load i64, ptr %a25
  %t30 = load i64, ptr %a3
  %t31 = icmp slt i64 %t29, %t30
  br i1 %t31, label %loop_body27, label %loop_exit28
loop_body27:
  %t32 = load ptr, ptr %a1
  %t33 = load i64, ptr %a25
  %t34 = load ptr, ptr %a2
  %t35 = load i64, ptr %a25
  %t36 = getelementptr i8, ptr %t34, i64 %t35
  %t37 = load volatile i8, ptr %t36, align 1
  %t38 = getelementptr i8, ptr %t32, i64 %t33
  store volatile i8 %t37, ptr %t38, align 1
  store i8 0, ptr %a39
  %t40 = load i64, ptr %a25
  %t41 = add i64 %t40, 1
  store i64 %t41, ptr %a25
  br label %loop_cond26
loop_exit28:
  %t42 = load i64, ptr %a25
  store i64 %t42, ptr %a43
  %t44 = load ptr, ptr %a1
  ret ptr %t44
}

; memmove  graph:46116cc90891da8a
define ptr @memmove(ptr %p_dst, ptr %p_src, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a3 = alloca i64
  %a9 = alloca ptr
  %a18 = alloca i64
  %a33 = alloca i8
  %a37 = alloca i64
  %a39 = alloca i64
  %a54 = alloca i8
  %a58 = alloca i64
  store ptr %p_dst, ptr %a1
  store ptr %p_src, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load ptr, ptr %a1
  %t5 = ptrtoint ptr %t4 to i64
  %t6 = load ptr, ptr %a2
  %t7 = ptrtoint ptr %t6 to i64
  %t8 = icmp sle i64 %t5, %t7
  br i1 %t8, label %then10, label %else11
then10:
  %t13 = load ptr, ptr %a1
  %t14 = load ptr, ptr %a2
  %t15 = load i64, ptr %a3
  %t16 = call ptr @memcpy(ptr %t13, ptr %t14, i64 %t15)
  store ptr %t16, ptr %a9
  br label %join12
else11:
  %t17 = load i64, ptr %a3
  store i64 %t17, ptr %a18
  br label %loop_cond19
loop_cond19:
  %t22 = load i64, ptr %a18
  %t23 = icmp sge i64 %t22, 8
  br i1 %t23, label %loop_body20, label %loop_exit21
loop_body20:
  %t24 = load ptr, ptr %a1
  %t25 = load i64, ptr %a18
  %t26 = sub i64 %t25, 8
  %t27 = load ptr, ptr %a2
  %t28 = load i64, ptr %a18
  %t29 = sub i64 %t28, 8
  %t30 = getelementptr i8, ptr %t27, i64 %t29
  %t31 = load volatile i64, ptr %t30, align 1
  %t32 = getelementptr i8, ptr %t24, i64 %t26
  store volatile i64 %t31, ptr %t32, align 1
  store i8 0, ptr %a33
  %t34 = load i64, ptr %a18
  %t35 = sub i64 %t34, 8
  store i64 %t35, ptr %a18
  br label %loop_cond19
loop_exit21:
  %t36 = load i64, ptr %a18
  store i64 %t36, ptr %a37
  %t38 = load i64, ptr %a37
  store i64 %t38, ptr %a39
  br label %loop_cond40
loop_cond40:
  %t43 = load i64, ptr %a39
  %t44 = icmp sgt i64 %t43, 0
  br i1 %t44, label %loop_body41, label %loop_exit42
loop_body41:
  %t45 = load ptr, ptr %a1
  %t46 = load i64, ptr %a39
  %t47 = sub i64 %t46, 1
  %t48 = load ptr, ptr %a2
  %t49 = load i64, ptr %a39
  %t50 = sub i64 %t49, 1
  %t51 = getelementptr i8, ptr %t48, i64 %t50
  %t52 = load volatile i8, ptr %t51, align 1
  %t53 = getelementptr i8, ptr %t45, i64 %t47
  store volatile i8 %t52, ptr %t53, align 1
  store i8 0, ptr %a54
  %t55 = load i64, ptr %a39
  %t56 = sub i64 %t55, 1
  store i64 %t56, ptr %a39
  br label %loop_cond40
loop_exit42:
  %t57 = load i64, ptr %a39
  store i64 %t57, ptr %a58
  %t59 = load ptr, ptr %a1
  store ptr %t59, ptr %a9
  br label %join12
join12:
  %t60 = load ptr, ptr %a9
  ret ptr %t60
}

; memset  graph:2e043a144089c8fd
define ptr @memset(ptr %p_dst, i32 %p_byte, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i32
  %a3 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a13 = alloca i64
  %a25 = alloca i8
  %a29 = alloca i64
  %a31 = alloca i64
  %a43 = alloca i8
  %a47 = alloca i64
  store ptr %p_dst, ptr %a1
  store i32 %p_byte, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load i32, ptr %a2
  %t5 = sext i32 %t4 to i64
  %t6 = srem i64 %t5, 256
  %t7 = add i64 %t6, 256
  %t8 = srem i64 %t7, 256
  store i64 %t8, ptr %a9
  %t10 = load i64, ptr %a9
  %t11 = mul i64 %t10, 72340172838076673
  store i64 %t11, ptr %a12
  store i64 0, ptr %a13
  br label %loop_cond14
loop_cond14:
  %t17 = load i64, ptr %a13
  %t18 = add i64 %t17, 8
  %t19 = load i64, ptr %a3
  %t20 = icmp sle i64 %t18, %t19
  br i1 %t20, label %loop_body15, label %loop_exit16
loop_body15:
  %t21 = load ptr, ptr %a1
  %t22 = load i64, ptr %a13
  %t23 = load i64, ptr %a12
  %t24 = getelementptr i8, ptr %t21, i64 %t22
  store volatile i64 %t23, ptr %t24, align 1
  store i8 0, ptr %a25
  %t26 = load i64, ptr %a13
  %t27 = add i64 %t26, 8
  store i64 %t27, ptr %a13
  br label %loop_cond14
loop_exit16:
  %t28 = load i64, ptr %a13
  store i64 %t28, ptr %a29
  %t30 = load i64, ptr %a29
  store i64 %t30, ptr %a31
  br label %loop_cond32
loop_cond32:
  %t35 = load i64, ptr %a31
  %t36 = load i64, ptr %a3
  %t37 = icmp slt i64 %t35, %t36
  br i1 %t37, label %loop_body33, label %loop_exit34
loop_body33:
  %t38 = load ptr, ptr %a1
  %t39 = load i64, ptr %a31
  %t40 = load i64, ptr %a9
  %t41 = trunc i64 %t40 to i8
  %t42 = getelementptr i8, ptr %t38, i64 %t39
  store volatile i8 %t41, ptr %t42, align 1
  store i8 0, ptr %a43
  %t44 = load i64, ptr %a31
  %t45 = add i64 %t44, 1
  store i64 %t45, ptr %a31
  br label %loop_cond32
loop_exit34:
  %t46 = load i64, ptr %a31
  store i64 %t46, ptr %a47
  %t48 = load ptr, ptr %a1
  ret ptr %t48
}

; bzero  graph:f5755c999e0d420e
define void @bzero(ptr %p_dst, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  %a7 = alloca ptr
  store ptr %p_dst, ptr %a1
  store i64 %p_n, ptr %a2
  %t3 = load ptr, ptr %a1
  %t4 = trunc i64 0 to i32
  %t5 = load i64, ptr %a2
  %t6 = call ptr @memset(ptr %t3, i32 %t4, i64 %t5)
  store ptr %t6, ptr %a7
  ret void
}

; ax_cap  graph:ab50ca90f9015acf
define i64 @ax_cap(i64 %p_bytes) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a9 = alloca i1
  store i64 %p_bytes, ptr %a1
  store i64 16, ptr %a2
  br label %loop_cond3
loop_cond3:
  %t6 = load i64, ptr %a2
  %t7 = load i64, ptr %a1
  %t8 = icmp slt i64 %t6, %t7
  store i1 %t8, ptr %a9
  br i1 %t8, label %rhs10, label %join11
rhs10:
  %t12 = load i64, ptr %a2
  %t13 = icmp sle i64 %t12, 4611686018427387903
  store i1 %t13, ptr %a9
  br label %join11
join11:
  %t14 = load i1, ptr %a9
  br i1 %t14, label %loop_body4, label %loop_exit5
loop_body4:
  %t15 = load i64, ptr %a2
  %t16 = mul i64 %t15, 2
  store i64 %t16, ptr %a2
  br label %loop_cond3
loop_exit5:
  %t17 = load i64, ptr %a2
  ret i64 %t17
}

; rt_class  graph:afeb6cae65c07e82
define internal i64 @ax_rt_class__par(i64 %p_capacity) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  store i64 %p_capacity, ptr %a1
  store i64 16, ptr %a2
  store i64 0, ptr %a3
  br label %loop_cond4
loop_cond4:
  %t7 = load i64, ptr %a2
  %t8 = load i64, ptr %a1
  %t9 = icmp slt i64 %t7, %t8
  br i1 %t9, label %loop_body5, label %loop_exit6
loop_body5:
  %t10 = load i64, ptr %a2
  %t11 = mul i64 %t10, 2
  %t12 = load i64, ptr %a3
  %t13 = add i64 %t12, 1
  store i64 %t11, ptr %a2
  store i64 %t13, ptr %a3
  br label %loop_cond4
loop_exit6:
  %t14 = load i64, ptr %a3
  ret i64 %t14
}

; rt_class  graph:afeb6cae65c07e82
define internal i64 @ax_rt_class__seq(i64 %p_capacity) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  store i64 %p_capacity, ptr %a1
  store i64 16, ptr %a2
  store i64 0, ptr %a3
  br label %loop_cond4
loop_cond4:
  %t7 = load i64, ptr %a2
  %t8 = load i64, ptr %a1
  %t9 = icmp slt i64 %t7, %t8
  br i1 %t9, label %loop_body5, label %loop_exit6
loop_body5:
  %t10 = load i64, ptr %a2
  %t11 = mul i64 %t10, 2
  %t12 = load i64, ptr %a3
  %t13 = add i64 %t12, 1
  store i64 %t11, ptr %a2
  store i64 %t13, ptr %a3
  br label %loop_cond4
loop_exit6:
  %t14 = load i64, ptr %a3
  ret i64 %t14
}

; rt_map  graph:f282e27ae07f19af
define internal ptr @ax_rt_map__seq(i64 %p_bytes) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca i64
  %a7 = alloca ptr
  %a15 = alloca i8
  store i64 %p_bytes, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 @ax_rt_mmap__seq(i64 %t2)
  store i64 %t3, ptr %a4
  %t5 = load i64, ptr %a4
  %t6 = icmp slt i64 %t5, 0
  br i1 %t6, label %then8, label %else9
then8:
  %t11 = insertvalue %ax_arr undef, ptr @.bytes.3, 0
  %t12 = insertvalue %ax_arr %t11, i64 12, 1
  %t13 = insertvalue %ax_arr %t12, i64 0, 2
  %t14 = extractvalue %ax_arr %t13, 0
  call void @ax_trap(ptr %t14)
  store i8 0, ptr %a15
  store ptr null, ptr %a7
  br label %join10
else9:
  %t16 = load i64, ptr %a4
  %t17 = inttoptr i64 %t16 to ptr
  store ptr %t17, ptr %a7
  br label %join10
join10:
  %t18 = load ptr, ptr %a7
  ret ptr %t18
}

; ax_alloc  graph:95e4411b0eb508fa
define ptr @ax_alloc(i64 %p_bytes) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca i1
  %a10 = alloca ptr
  %a18 = alloca i8
  %a21 = alloca i64
  %a24 = alloca i64
  %a25 = alloca ptr
  %a32 = alloca ptr
  %a35 = alloca ptr
  %a47 = alloca i8
  %a60 = alloca i8
  %a64 = alloca ptr
  %a74 = alloca i64
  %a79 = alloca i8
  %a86 = alloca i8
  %a90 = alloca i8
  %a94 = alloca ptr
  %a101 = alloca i8
  %a110 = alloca i8
  %a113 = alloca ptr
  %a117 = alloca i8
  %a121 = alloca i64
  %a127 = alloca i8
  store i64 %p_bytes, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = icmp slt i64 %t2, 0
  store i1 %t3, ptr %a4
  br i1 %t3, label %join6, label %rhs5
rhs5:
  %t7 = load i64, ptr %a1
  %t8 = icmp sgt i64 %t7, 4611686018427387904
  store i1 %t8, ptr %a4
  br label %join6
join6:
  %t9 = load i1, ptr %a4
  br i1 %t9, label %then11, label %else12
then11:
  %t14 = insertvalue %ax_arr undef, ptr @.bytes.4, 0
  %t15 = insertvalue %ax_arr %t14, i64 29, 1
  %t16 = insertvalue %ax_arr %t15, i64 0, 2
  %t17 = extractvalue %ax_arr %t16, 0
  call void @ax_trap(ptr %t17)
  store i8 0, ptr %a18
  store ptr null, ptr %a10
  br label %join13
else12:
  %t19 = load i64, ptr %a1
  %t20 = call i64 @ax_cap(i64 %t19)
  store i64 %t20, ptr %a21
  %t22 = load i64, ptr %a21
  %t23 = call i64 @ax_rt_class__seq(i64 %t22)
  store i64 %t23, ptr %a24
  store ptr @ax_runtime_state, ptr %a25
  %t26 = load ptr, ptr %a25
  %t27 = load i64, ptr %a24
  %t28 = mul i64 %t27, 8
  %t29 = add i64 256, %t28
  %t30 = getelementptr i8, ptr %t26, i64 %t29
  %t31 = load ptr, ptr %t30, align 1
  store ptr %t31, ptr %a32
  %t33 = load ptr, ptr %a32
  %t34 = icmp ne ptr %t33, null
  br i1 %t34, label %then36, label %else37
then36:
  %t39 = load ptr, ptr %a25
  %t40 = load i64, ptr %a24
  %t41 = mul i64 %t40, 8
  %t42 = add i64 256, %t41
  %t43 = load ptr, ptr %a32
  %t44 = getelementptr i8, ptr %t43, i64 0
  %t45 = load ptr, ptr %t44, align 1
  %t46 = getelementptr i8, ptr %t39, i64 %t42
  store ptr %t45, ptr %t46, align 1
  store i8 0, ptr %a47
  %t48 = load ptr, ptr %a25
  %t49 = load i64, ptr %a24
  %t50 = mul i64 %t49, 8
  %t51 = add i64 768, %t50
  %t52 = load ptr, ptr %a25
  %t53 = load i64, ptr %a24
  %t54 = mul i64 %t53, 8
  %t55 = add i64 768, %t54
  %t56 = getelementptr i8, ptr %t52, i64 %t55
  %t57 = load i64, ptr %t56, align 1
  %t58 = sub i64 %t57, 1
  %t59 = getelementptr i8, ptr %t48, i64 %t51
  store i64 %t58, ptr %t59, align 1
  store i8 0, ptr %a60
  %t61 = load ptr, ptr %a32
  store ptr %t61, ptr %a35
  br label %join38
else37:
  %t62 = load i64, ptr %a21
  %t63 = icmp sgt i64 %t62, 32768
  br i1 %t63, label %then65, label %else66
then65:
  %t68 = load i64, ptr %a21
  %t69 = add i64 %t68, 16
  %t70 = call ptr @ax_rt_map__seq(i64 %t69)
  store ptr %t70, ptr %a64
  br label %join67
else66:
  %t71 = load ptr, ptr %a25
  %t72 = getelementptr i8, ptr %t71, i64 32
  %t73 = load i64, ptr %t72, align 1
  store i64 %t73, ptr %a74
  %t75 = load i64, ptr %a74
  %t76 = load i64, ptr %a21
  %t77 = add i64 %t76, 16
  %t78 = icmp slt i64 %t75, %t77
  br i1 %t78, label %then80, label %else81
then80:
  %t83 = load ptr, ptr %a25
  %t84 = call ptr @ax_rt_map__seq(i64 65536)
  %t85 = getelementptr i8, ptr %t83, i64 24
  store ptr %t84, ptr %t85, align 1
  store i8 0, ptr %a86
  %t87 = load ptr, ptr %a25
  %t88 = getelementptr i8, ptr %t87, i64 32
  store i64 65536, ptr %t88, align 1
  store i8 0, ptr %a79
  br label %join82
else81:
  store i8 0, ptr %a79
  br label %join82
join82:
  %t89 = load i8, ptr %a79
  store i8 %t89, ptr %a90
  %t91 = load ptr, ptr %a25
  %t92 = getelementptr i8, ptr %t91, i64 24
  %t93 = load ptr, ptr %t92, align 1
  store ptr %t93, ptr %a94
  %t95 = load ptr, ptr %a25
  %t96 = load ptr, ptr %a94
  %t97 = load i64, ptr %a21
  %t98 = add i64 %t97, 16
  %t99 = getelementptr i8, ptr %t96, i64 %t98
  %t100 = getelementptr i8, ptr %t95, i64 24
  store ptr %t99, ptr %t100, align 1
  store i8 0, ptr %a101
  %t102 = load ptr, ptr %a25
  %t103 = load ptr, ptr %a25
  %t104 = getelementptr i8, ptr %t103, i64 32
  %t105 = load i64, ptr %t104, align 1
  %t106 = load i64, ptr %a21
  %t107 = sub i64 %t105, %t106
  %t108 = sub i64 %t107, 16
  %t109 = getelementptr i8, ptr %t102, i64 32
  store i64 %t108, ptr %t109, align 1
  store i8 0, ptr %a110
  %t111 = load ptr, ptr %a94
  store ptr %t111, ptr %a64
  br label %join67
join67:
  %t112 = load ptr, ptr %a64
  store ptr %t112, ptr %a113
  %t114 = load ptr, ptr %a113
  %t115 = load i64, ptr %a21
  %t116 = getelementptr i8, ptr %t114, i64 0
  store i64 %t115, ptr %t116, align 1
  store i8 0, ptr %a117
  %t118 = load ptr, ptr %a113
  %t119 = load i64, ptr %a21
  %t120 = icmp sle i64 %t119, 32768
  br i1 %t120, label %then122, label %else123
then122:
  store i64 1, ptr %a121
  br label %join124
else123:
  store i64 0, ptr %a121
  br label %join124
join124:
  %t125 = load i64, ptr %a121
  %t126 = getelementptr i8, ptr %t118, i64 8
  store i64 %t125, ptr %t126, align 1
  store i8 0, ptr %a127
  %t128 = load ptr, ptr %a113
  %t129 = getelementptr i8, ptr %t128, i64 16
  store ptr %t129, ptr %a35
  br label %join38
join38:
  %t130 = load ptr, ptr %a35
  store ptr %t130, ptr %a10
  br label %join13
join13:
  %t131 = load ptr, ptr %a10
  ret ptr %t131
}

; ax_release  graph:3d06b50bfe10a6db
define internal void @ax_ax_release__seq(ptr %p_p) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a4 = alloca i8
  %a11 = alloca i64
  %a14 = alloca i64
  %a15 = alloca ptr
  %a22 = alloca i64
  %a27 = alloca i1
  %a33 = alloca i8
  %a42 = alloca i64
  %a51 = alloca i8
  %a58 = alloca i8
  store ptr %p_p, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = icmp eq ptr %t2, null
  br i1 %t3, label %then5, label %else6
then5:
  store i8 0, ptr %a4
  br label %join7
else6:
  %t8 = load ptr, ptr %a1
  %t9 = getelementptr i8, ptr %t8, i64 -16
  %t10 = load i64, ptr %t9, align 1
  store i64 %t10, ptr %a11
  %t12 = load i64, ptr %a11
  %t13 = call i64 @ax_rt_class__seq(i64 %t12)
  store i64 %t13, ptr %a14
  store ptr @ax_runtime_state, ptr %a15
  %t16 = load ptr, ptr %a15
  %t17 = load i64, ptr %a14
  %t18 = mul i64 %t17, 8
  %t19 = add i64 768, %t18
  %t20 = getelementptr i8, ptr %t16, i64 %t19
  %t21 = load i64, ptr %t20, align 1
  store i64 %t21, ptr %a22
  %t23 = load ptr, ptr %a1
  %t24 = getelementptr i8, ptr %t23, i64 -8
  %t25 = load i64, ptr %t24, align 1
  %t26 = icmp eq i64 %t25, 0
  store i1 %t26, ptr %a27
  br i1 %t26, label %rhs28, label %join29
rhs28:
  %t30 = load i64, ptr %a22
  %t31 = icmp sge i64 %t30, 8
  store i1 %t31, ptr %a27
  br label %join29
join29:
  %t32 = load i1, ptr %a27
  br i1 %t32, label %then34, label %else35
then34:
  %t37 = load ptr, ptr %a1
  %t38 = getelementptr i8, ptr %t37, i64 -16
  %t39 = load i64, ptr %a11
  %t40 = add i64 %t39, 16
  %t41 = call i64 @ax_rt_munmap__seq(ptr %t38, i64 %t40)
  store i64 %t41, ptr %a42
  store i8 0, ptr %a33
  br label %join36
else35:
  %t43 = load ptr, ptr %a1
  %t44 = load ptr, ptr %a15
  %t45 = load i64, ptr %a14
  %t46 = mul i64 %t45, 8
  %t47 = add i64 256, %t46
  %t48 = getelementptr i8, ptr %t44, i64 %t47
  %t49 = load ptr, ptr %t48, align 1
  %t50 = getelementptr i8, ptr %t43, i64 0
  store ptr %t49, ptr %t50, align 1
  store i8 0, ptr %a51
  %t52 = load ptr, ptr %a15
  %t53 = load i64, ptr %a14
  %t54 = mul i64 %t53, 8
  %t55 = add i64 256, %t54
  %t56 = load ptr, ptr %a1
  %t57 = getelementptr i8, ptr %t52, i64 %t55
  store ptr %t56, ptr %t57, align 1
  store i8 0, ptr %a58
  %t59 = load ptr, ptr %a15
  %t60 = load i64, ptr %a14
  %t61 = mul i64 %t60, 8
  %t62 = add i64 768, %t61
  %t63 = load i64, ptr %a22
  %t64 = add i64 %t63, 1
  %t65 = getelementptr i8, ptr %t59, i64 %t62
  store i64 %t64, ptr %t65, align 1
  store i8 0, ptr %a33
  br label %join36
join36:
  %t66 = load i8, ptr %a33
  store i8 %t66, ptr %a4
  br label %join7
join7:
  %t67 = load i8, ptr %a4
  ret void
}

; ax_free  graph:1b2fe573025f6db5
define void @ax_free(ptr %p_p, i64 %p_bytes) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  store ptr %p_p, ptr %a1
  store i64 %p_bytes, ptr %a2
  %t3 = load ptr, ptr %a1
  call void @ax_ax_release__seq(ptr %t3)
  ret void
}

; calloc  graph:f62f9f7b7b3ef2fe
define ptr @calloc(i64 %p_n, i64 %p_size) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a5 = alloca i1
  %a11 = alloca i1
  %a16 = alloca i1
  %a25 = alloca ptr
  %a33 = alloca i8
  %a37 = alloca i64
  %a40 = alloca ptr
  store i64 %p_n, ptr %a1
  store i64 %p_size, ptr %a2
  %t3 = load i64, ptr %a1
  %t4 = icmp slt i64 %t3, 0
  store i1 %t4, ptr %a5
  br i1 %t4, label %join7, label %rhs6
rhs6:
  %t8 = load i64, ptr %a2
  %t9 = icmp slt i64 %t8, 0
  store i1 %t9, ptr %a5
  br label %join7
join7:
  %t10 = load i1, ptr %a5
  store i1 %t10, ptr %a11
  br i1 %t10, label %join13, label %rhs12
rhs12:
  %t14 = load i64, ptr %a2
  %t15 = icmp sgt i64 %t14, 0
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  %t19 = load i64, ptr %a1
  %t20 = load i64, ptr %a2
  %t21 = sdiv i64 9223372036854775807, %t20
  %t22 = icmp sgt i64 %t19, %t21
  store i1 %t22, ptr %a16
  br label %join18
join18:
  %t23 = load i1, ptr %a16
  store i1 %t23, ptr %a11
  br label %join13
join13:
  %t24 = load i1, ptr %a11
  br i1 %t24, label %then26, label %else27
then26:
  %t29 = insertvalue %ax_arr undef, ptr @.bytes.5, 0
  %t30 = insertvalue %ax_arr %t29, i64 16, 1
  %t31 = insertvalue %ax_arr %t30, i64 0, 2
  %t32 = extractvalue %ax_arr %t31, 0
  call void @ax_trap(ptr %t32)
  store i8 0, ptr %a33
  store ptr null, ptr %a25
  br label %join28
else27:
  %t34 = load i64, ptr %a1
  %t35 = load i64, ptr %a2
  %t36 = mul i64 %t34, %t35
  store i64 %t36, ptr %a37
  %t38 = load i64, ptr %a37
  %t39 = call ptr @ax_alloc(i64 %t38)
  store ptr %t39, ptr %a40
  %t41 = load ptr, ptr %a40
  %t42 = trunc i64 0 to i32
  %t43 = load i64, ptr %a37
  %t44 = call ptr @memset(ptr %t41, i32 %t42, i64 %t43)
  store ptr %t44, ptr %a25
  br label %join28
join28:
  %t45 = load ptr, ptr %a25
  ret ptr %t45
}

; rt_fork  graph:c02f043438a3bb38
define internal i64 @ax_rt_fork__seq() "no-builtins" {
entry:
  %a2 = alloca i64
  %a5 = alloca i64
  %a13 = alloca ptr
  %t1 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 17, i64 0, i64 0, i64 0, i64 0, i64 0, i64 220)
  store i64 %t1, ptr %a2
  %t3 = load i64, ptr %a2
  %t4 = icmp ne i64 %t3, 0
  br i1 %t4, label %then6, label %else7
then6:
  %t9 = load i64, ptr %a2
  store i64 %t9, ptr %a5
  br label %join8
else7:
  %t10 = getelementptr i8, ptr @ax_runtime_state, i64 24
  %t11 = trunc i64 0 to i32
  %t12 = call ptr @memset(ptr %t10, i32 %t11, i64 2024)
  store ptr %t12, ptr %a13
  store i64 0, ptr %a5
  br label %join8
join8:
  %t14 = load i64, ptr %a5
  ret i64 %t14
}

; rt_env_match  graph:d62c7306a3490c42
define internal i1 @ax_rt_env_match__seq(ptr %p_entry, ptr %p_name) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a5 = alloca i64
  %a6 = alloca i64
  %a7 = alloca i1
  %a12 = alloca i1
  %a31 = alloca i1
  %a33 = alloca i1
  store ptr %p_entry, ptr %a1
  store ptr %p_name, ptr %a2
  %t3 = load ptr, ptr %a2
  %t4 = call i64 @ax_rt_cstrlen__seq(ptr %t3)
  store i64 %t4, ptr %a5
  store i64 0, ptr %a6
  store i1 true, ptr %a7
  br label %loop_cond8
loop_cond8:
  %t11 = load i1, ptr %a7
  store i1 %t11, ptr %a12
  br i1 %t11, label %rhs13, label %join14
rhs13:
  %t15 = load i64, ptr %a6
  %t16 = load i64, ptr %a5
  %t17 = icmp slt i64 %t15, %t16
  store i1 %t17, ptr %a12
  br label %join14
join14:
  %t18 = load i1, ptr %a12
  br i1 %t18, label %loop_body9, label %loop_exit10
loop_body9:
  %t19 = load i64, ptr %a6
  %t20 = add i64 %t19, 1
  %t21 = load ptr, ptr %a1
  %t22 = load i64, ptr %a6
  %t23 = getelementptr i8, ptr %t21, i64 %t22
  %t24 = load i8, ptr %t23, align 1
  %t25 = load ptr, ptr %a2
  %t26 = load i64, ptr %a6
  %t27 = getelementptr i8, ptr %t25, i64 %t26
  %t28 = load i8, ptr %t27, align 1
  %t29 = icmp eq i8 %t24, %t28
  store i64 %t20, ptr %a6
  store i1 %t29, ptr %a7
  br label %loop_cond8
loop_exit10:
  %t30 = load i1, ptr %a7
  store i1 %t30, ptr %a31
  %t32 = load i1, ptr %a31
  store i1 %t32, ptr %a33
  br i1 %t32, label %rhs34, label %join35
rhs34:
  %t36 = load ptr, ptr %a1
  %t37 = load i64, ptr %a5
  %t38 = getelementptr i8, ptr %t36, i64 %t37
  %t39 = load i8, ptr %t38, align 1
  %t40 = icmp eq i8 %t39, 61
  store i1 %t40, ptr %a33
  br label %join35
join35:
  %t41 = load i1, ptr %a33
  ret i1 %t41
}

; rt_getenv  graph:03c84845afa383a6
define internal ptr @ax_rt_getenv__seq(ptr %p_name) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a4 = alloca ptr
  %a7 = alloca ptr
  %a11 = alloca i64
  %a12 = alloca ptr
  %a18 = alloca i1
  %a35 = alloca ptr
  %a39 = alloca ptr
  store ptr %p_name, ptr %a1
  %t2 = getelementptr i8, ptr @ax_runtime_state, i64 0
  %t3 = load ptr, ptr %t2, align 1
  store ptr %t3, ptr %a4
  %t5 = load ptr, ptr %a4
  %t6 = icmp eq ptr %t5, null
  br i1 %t6, label %then8, label %else9
then8:
  store ptr null, ptr %a7
  br label %join10
else9:
  store i64 0, ptr %a11
  store ptr null, ptr %a12
  br label %loop_cond13
loop_cond13:
  %t16 = load ptr, ptr %a12
  %t17 = icmp eq ptr %t16, null
  store i1 %t17, ptr %a18
  br i1 %t17, label %rhs19, label %join20
rhs19:
  %t21 = load ptr, ptr %a4
  %t22 = load i64, ptr %a11
  %t23 = mul i64 %t22, 8
  %t24 = getelementptr i8, ptr %t21, i64 %t23
  %t25 = load ptr, ptr %t24, align 1
  %t26 = icmp ne ptr %t25, null
  store i1 %t26, ptr %a18
  br label %join20
join20:
  %t27 = load i1, ptr %a18
  br i1 %t27, label %loop_body14, label %loop_exit15
loop_body14:
  %t28 = load i64, ptr %a11
  %t29 = add i64 %t28, 1
  %t30 = load ptr, ptr %a4
  %t31 = load i64, ptr %a11
  %t32 = mul i64 %t31, 8
  %t33 = getelementptr i8, ptr %t30, i64 %t32
  %t34 = load ptr, ptr %t33, align 1
  store ptr %t34, ptr %a35
  %t36 = load ptr, ptr %a35
  %t37 = load ptr, ptr %a1
  %t38 = call i1 @ax_rt_env_match__seq(ptr %t36, ptr %t37)
  br i1 %t38, label %then40, label %else41
then40:
  %t43 = load ptr, ptr %a35
  %t44 = load ptr, ptr %a1
  %t45 = call i64 @ax_rt_cstrlen__seq(ptr %t44)
  %t46 = add i64 %t45, 1
  %t47 = getelementptr i8, ptr %t43, i64 %t46
  store ptr %t47, ptr %a39
  br label %join42
else41:
  store ptr null, ptr %a39
  br label %join42
join42:
  %t48 = load ptr, ptr %a39
  store i64 %t29, ptr %a11
  store ptr %t48, ptr %a12
  br label %loop_cond13
loop_exit15:
  %t49 = load ptr, ptr %a12
  store ptr %t49, ptr %a7
  br label %join10
join10:
  %t50 = load ptr, ptr %a7
  ret ptr %t50
}

; rt_digit_ok  graph:01ef19facbab700b
define internal i1 @ax_rt_digit_ok__par(i64 %p_acc, i64 %p_digit, i1 %p_negative) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i1
  %a6 = alloca i1
  %a12 = alloca i1
  %a18 = alloca i1
  %a23 = alloca i1
  %a28 = alloca i64
  store i64 %p_acc, ptr %a1
  store i64 %p_digit, ptr %a2
  store i1 %p_negative, ptr %a3
  %t4 = load i64, ptr %a2
  %t5 = icmp sge i64 %t4, 0
  store i1 %t5, ptr %a6
  br i1 %t5, label %rhs7, label %join8
rhs7:
  %t9 = load i64, ptr %a2
  %t10 = icmp sle i64 %t9, 9
  store i1 %t10, ptr %a6
  br label %join8
join8:
  %t11 = load i1, ptr %a6
  store i1 %t11, ptr %a12
  br i1 %t11, label %rhs13, label %join14
rhs13:
  %t15 = load i64, ptr %a1
  %t16 = icmp sge i64 %t15, -922337203685477580
  store i1 %t16, ptr %a12
  br label %join14
join14:
  %t17 = load i1, ptr %a12
  store i1 %t17, ptr %a18
  br i1 %t17, label %rhs19, label %join20
rhs19:
  %t21 = load i64, ptr %a1
  %t22 = icmp ne i64 %t21, -922337203685477580
  store i1 %t22, ptr %a23
  br i1 %t22, label %join25, label %rhs24
rhs24:
  %t26 = load i64, ptr %a2
  %t27 = load i1, ptr %a3
  br i1 %t27, label %then29, label %else30
then29:
  store i64 8, ptr %a28
  br label %join31
else30:
  store i64 7, ptr %a28
  br label %join31
join31:
  %t32 = load i64, ptr %a28
  %t33 = icmp sle i64 %t26, %t32
  store i1 %t33, ptr %a23
  br label %join25
join25:
  %t34 = load i1, ptr %a23
  store i1 %t34, ptr %a18
  br label %join20
join20:
  %t35 = load i1, ptr %a18
  ret i1 %t35
}

; rt_digit_ok  graph:01ef19facbab700b
define internal i1 @ax_rt_digit_ok__seq(i64 %p_acc, i64 %p_digit, i1 %p_negative) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i1
  %a6 = alloca i1
  %a12 = alloca i1
  %a18 = alloca i1
  %a23 = alloca i1
  %a28 = alloca i64
  store i64 %p_acc, ptr %a1
  store i64 %p_digit, ptr %a2
  store i1 %p_negative, ptr %a3
  %t4 = load i64, ptr %a2
  %t5 = icmp sge i64 %t4, 0
  store i1 %t5, ptr %a6
  br i1 %t5, label %rhs7, label %join8
rhs7:
  %t9 = load i64, ptr %a2
  %t10 = icmp sle i64 %t9, 9
  store i1 %t10, ptr %a6
  br label %join8
join8:
  %t11 = load i1, ptr %a6
  store i1 %t11, ptr %a12
  br i1 %t11, label %rhs13, label %join14
rhs13:
  %t15 = load i64, ptr %a1
  %t16 = icmp sge i64 %t15, -922337203685477580
  store i1 %t16, ptr %a12
  br label %join14
join14:
  %t17 = load i1, ptr %a12
  store i1 %t17, ptr %a18
  br i1 %t17, label %rhs19, label %join20
rhs19:
  %t21 = load i64, ptr %a1
  %t22 = icmp ne i64 %t21, -922337203685477580
  store i1 %t22, ptr %a23
  br i1 %t22, label %join25, label %rhs24
rhs24:
  %t26 = load i64, ptr %a2
  %t27 = load i1, ptr %a3
  br i1 %t27, label %then29, label %else30
then29:
  store i64 8, ptr %a28
  br label %join31
else30:
  store i64 7, ptr %a28
  br label %join31
join31:
  %t32 = load i64, ptr %a28
  %t33 = icmp sle i64 %t26, %t32
  store i1 %t33, ptr %a23
  br label %join25
join25:
  %t34 = load i1, ptr %a23
  store i1 %t34, ptr %a18
  br label %join20
join20:
  %t35 = load i1, ptr %a18
  ret i1 %t35
}

; ax_parse_i64  graph:aae94e44a3c2e3a4
define i64 @ax_parse_i64(ptr %p_text, ptr %p_name) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a6 = alloca i8
  %a9 = alloca i1
  %a11 = alloca i1
  %a17 = alloca i64
  %a22 = alloca i64
  %a24 = alloca i64
  %a25 = alloca i64
  %a26 = alloca i1
  %a27 = alloca i64
  %a32 = alloca i1
  %a50 = alloca i64
  %a55 = alloca i64
  %a78 = alloca i1
  %a84 = alloca i64
  %a92 = alloca i8
  %a94 = alloca i8
  %a99 = alloca i8
  %a101 = alloca i8
  %a106 = alloca i8
  %a107 = alloca i8
  %a109 = alloca i64
  store ptr %p_text, ptr %a1
  store ptr %p_name, ptr %a2
  %t3 = load ptr, ptr %a1
  %t4 = getelementptr i8, ptr %t3, i64 0
  %t5 = load i8, ptr %t4, align 1
  store i8 %t5, ptr %a6
  %t7 = load i8, ptr %a6
  %t8 = icmp eq i8 %t7, 45
  store i1 %t8, ptr %a9
  %t10 = load i1, ptr %a9
  store i1 %t10, ptr %a11
  br i1 %t10, label %join13, label %rhs12
rhs12:
  %t14 = load i8, ptr %a6
  %t15 = icmp eq i8 %t14, 43
  store i1 %t15, ptr %a11
  br label %join13
join13:
  %t16 = load i1, ptr %a11
  br i1 %t16, label %then18, label %else19
then18:
  store i64 1, ptr %a17
  br label %join20
else19:
  store i64 0, ptr %a17
  br label %join20
join20:
  %t21 = load i64, ptr %a17
  store i64 %t21, ptr %a22
  %t23 = load i64, ptr %a22
  store i64 %t23, ptr %a24
  store i64 0, ptr %a25
  store i1 true, ptr %a26
  store i64 0, ptr %a27
  br label %loop_cond28
loop_cond28:
  %t31 = load i1, ptr %a26
  store i1 %t31, ptr %a32
  br i1 %t31, label %rhs33, label %join34
rhs33:
  %t35 = load ptr, ptr %a1
  %t36 = load i64, ptr %a24
  %t37 = getelementptr i8, ptr %t35, i64 %t36
  %t38 = load i8, ptr %t37, align 1
  %t39 = trunc i64 0 to i8
  %t40 = icmp ne i8 %t38, %t39
  store i1 %t40, ptr %a32
  br label %join34
join34:
  %t41 = load i1, ptr %a32
  br i1 %t41, label %loop_body29, label %loop_exit30
loop_body29:
  %t42 = load i64, ptr %a24
  %t43 = add i64 %t42, 1
  %t44 = load ptr, ptr %a1
  %t45 = load i64, ptr %a24
  %t46 = getelementptr i8, ptr %t44, i64 %t45
  %t47 = load i8, ptr %t46, align 1
  %t48 = zext i8 %t47 to i64
  %t49 = sub i64 %t48, 48
  store i64 %t49, ptr %a50
  %t51 = load i64, ptr %a25
  %t52 = load i64, ptr %a50
  %t53 = load i1, ptr %a9
  %t54 = call i1 @ax_rt_digit_ok__seq(i64 %t51, i64 %t52, i1 %t53)
  br i1 %t54, label %then56, label %else57
then56:
  %t59 = load i64, ptr %a25
  %t60 = mul i64 %t59, 10
  %t61 = load i64, ptr %a50
  %t62 = sub i64 %t60, %t61
  store i64 %t62, ptr %a55
  br label %join58
else57:
  %t63 = load i64, ptr %a25
  store i64 %t63, ptr %a55
  br label %join58
join58:
  %t64 = load i64, ptr %a55
  %t65 = load i64, ptr %a25
  %t66 = load ptr, ptr %a1
  %t67 = load i64, ptr %a24
  %t68 = getelementptr i8, ptr %t66, i64 %t67
  %t69 = load i8, ptr %t68, align 1
  %t70 = zext i8 %t69 to i64
  %t71 = sub i64 %t70, 48
  %t72 = load i1, ptr %a9
  %t73 = call i1 @ax_rt_digit_ok__seq(i64 %t65, i64 %t71, i1 %t72)
  %t74 = load i64, ptr %a27
  %t75 = add i64 %t74, 1
  store i64 %t43, ptr %a24
  store i64 %t64, ptr %a25
  store i1 %t73, ptr %a26
  store i64 %t75, ptr %a27
  br label %loop_cond28
loop_exit30:
  %t76 = load i1, ptr %a26
  %t77 = xor i1 %t76, true
  store i1 %t77, ptr %a78
  br i1 %t77, label %join80, label %rhs79
rhs79:
  %t81 = load i64, ptr %a27
  %t82 = icmp eq i64 %t81, 0
  store i1 %t82, ptr %a78
  br label %join80
join80:
  %t83 = load i1, ptr %a78
  br i1 %t83, label %then85, label %else86
then85:
  %t88 = insertvalue %ax_arr undef, ptr @.bytes.6, 0
  %t89 = insertvalue %ax_arr %t88, i64 15, 1
  %t90 = insertvalue %ax_arr %t89, i64 0, 2
  %t91 = extractvalue %ax_arr %t90, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t91, i64 15)
  store i8 0, ptr %a92
  %t93 = load ptr, ptr %a2
  call void @ax_rt_puts__seq(i64 2, ptr %t93)
  store i8 0, ptr %a94
  %t95 = insertvalue %ax_arr undef, ptr @.bytes.7, 0
  %t96 = insertvalue %ax_arr %t95, i64 18, 1
  %t97 = insertvalue %ax_arr %t96, i64 0, 2
  %t98 = extractvalue %ax_arr %t97, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t98, i64 18)
  store i8 0, ptr %a99
  %t100 = load ptr, ptr %a1
  call void @ax_rt_puts__seq(i64 2, ptr %t100)
  store i8 0, ptr %a101
  %t102 = insertvalue %ax_arr undef, ptr @.bytes.2, 0
  %t103 = insertvalue %ax_arr %t102, i64 1, 1
  %t104 = insertvalue %ax_arr %t103, i64 0, 2
  %t105 = extractvalue %ax_arr %t104, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t105, i64 1)
  store i8 0, ptr %a106
  call void @ax_exit(i64 2)
  store i8 0, ptr %a107
  store i64 0, ptr %a84
  br label %join87
else86:
  %t108 = load i1, ptr %a9
  br i1 %t108, label %then110, label %else111
then110:
  %t113 = load i64, ptr %a25
  store i64 %t113, ptr %a109
  br label %join112
else111:
  %t114 = load i64, ptr %a25
  %t115 = sub i64 0, %t114
  store i64 %t115, ptr %a109
  br label %join112
join112:
  %t116 = load i64, ptr %a109
  store i64 %t116, ptr %a84
  br label %join87
join87:
  %t117 = load i64, ptr %a84
  ret i64 %t117
}

; rt_threads  graph:b2e8ad48101d9c5a
define internal i64 @ax_rt_threads__seq() "no-builtins" {
entry:
  %a6 = alloca ptr
  %a9 = alloca i64
  %a21 = alloca i64
  %a24 = alloca i64
  %a30 = alloca i64
  %t1 = insertvalue %ax_arr undef, ptr @.bytes.8, 0
  %t2 = insertvalue %ax_arr %t1, i64 13, 1
  %t3 = insertvalue %ax_arr %t2, i64 0, 2
  %t4 = extractvalue %ax_arr %t3, 0
  %t5 = call ptr @ax_rt_getenv__seq(ptr %t4)
  store ptr %t5, ptr %a6
  %t7 = load ptr, ptr %a6
  %t8 = icmp eq ptr %t7, null
  br i1 %t8, label %then10, label %else11
then10:
  %t13 = call i64 @ax_rt_ncpu__seq()
  store i64 %t13, ptr %a9
  br label %join12
else11:
  %t14 = load ptr, ptr %a6
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.8, 0
  %t16 = insertvalue %ax_arr %t15, i64 13, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = extractvalue %ax_arr %t17, 0
  %t19 = call i64 @ax_parse_i64(ptr %t14, ptr %t18)
  store i64 %t19, ptr %a9
  br label %join12
join12:
  %t20 = load i64, ptr %a9
  store i64 %t20, ptr %a21
  %t22 = load i64, ptr %a21
  %t23 = icmp slt i64 %t22, 1
  br i1 %t23, label %then25, label %else26
then25:
  store i64 1, ptr %a24
  br label %join27
else26:
  %t28 = load i64, ptr %a21
  %t29 = icmp sgt i64 %t28, 256
  br i1 %t29, label %then31, label %else32
then31:
  store i64 256, ptr %a30
  br label %join33
else32:
  %t34 = load i64, ptr %a21
  store i64 %t34, ptr %a30
  br label %join33
join33:
  %t35 = load i64, ptr %a30
  store i64 %t35, ptr %a24
  br label %join27
join27:
  %t36 = load i64, ptr %a24
  ret i64 %t36
}

; ax_chunks  graph:06ba8f92c07314ff
define i64 @ax_chunks(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca i64
  %a6 = alloca i64
  %a12 = alloca i1
  %a18 = alloca i64
  %a26 = alloca i64
  store i64 %p_n, ptr %a1
  %t2 = call i64 @ax_rt_threads__seq()
  store i64 %t2, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = icmp sle i64 %t4, 0
  br i1 %t5, label %then7, label %else8
then7:
  store i64 0, ptr %a6
  br label %join9
else8:
  %t10 = load i64, ptr %a3
  %t11 = icmp eq i64 %t10, 1
  store i1 %t11, ptr %a12
  br i1 %t11, label %join14, label %rhs13
rhs13:
  %t15 = load i64, ptr %a1
  %t16 = icmp slt i64 %t15, 1024
  store i1 %t16, ptr %a12
  br label %join14
join14:
  %t17 = load i1, ptr %a12
  br i1 %t17, label %then19, label %else20
then19:
  store i64 1, ptr %a18
  br label %join21
else20:
  %t22 = load i64, ptr %a1
  %t23 = load i64, ptr %a3
  %t24 = mul i64 %t23, 8
  %t25 = icmp slt i64 %t22, %t24
  br i1 %t25, label %then27, label %else28
then27:
  %t30 = load i64, ptr %a1
  store i64 %t30, ptr %a26
  br label %join29
else28:
  %t31 = load i64, ptr %a3
  %t32 = mul i64 %t31, 8
  store i64 %t32, ptr %a26
  br label %join29
join29:
  %t33 = load i64, ptr %a26
  store i64 %t33, ptr %a18
  br label %join21
join21:
  %t34 = load i64, ptr %a18
  store i64 %t34, ptr %a6
  br label %join9
join9:
  %t35 = load i64, ptr %a6
  ret i64 %t35
}

; ax_par_for  graph:fd30261b146b896d
define void @ax_par_for(i64 %p_chunks, ptr %p_work, ptr %p_context) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a6 = alloca i8
  %a11 = alloca i64
  %a15 = alloca i64
  %a22 = alloca i64
  %a24 = alloca ptr
  %a25 = alloca i64
  %a34 = alloca i64
  %a37 = alloca i64
  %a46 = alloca i64
  %a61 = alloca i8
  %a65 = alloca i64
  %a66 = alloca i8
  %a73 = alloca i8
  %a76 = alloca i8
  %a85 = alloca i64
  %a100 = alloca i8
  %a104 = alloca i64
  %a106 = alloca i8
  %a111 = alloca i64
  %a118 = alloca i64
  %a128 = alloca i8
  %a132 = alloca i64
  %a133 = alloca i64
  %a146 = alloca i64
  %a149 = alloca i64
  %a156 = alloca i64
  %a159 = alloca i8
  %a168 = alloca i8
  %a172 = alloca i64
  store i64 %p_chunks, ptr %a1
  store ptr %p_work, ptr %a2
  store ptr %p_context, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = icmp sle i64 %t4, 0
  br i1 %t5, label %then7, label %else8
then7:
  store i8 0, ptr %a6
  br label %join9
else8:
  %t10 = call i64 @ax_rt_threads__seq()
  store i64 %t10, ptr %a11
  %t12 = load i64, ptr %a1
  %t13 = load i64, ptr %a11
  %t14 = icmp slt i64 %t12, %t13
  br i1 %t14, label %then16, label %else17
then16:
  %t19 = load i64, ptr %a1
  store i64 %t19, ptr %a15
  br label %join18
else17:
  %t20 = load i64, ptr %a11
  store i64 %t20, ptr %a15
  br label %join18
join18:
  %t21 = load i64, ptr %a15
  store i64 %t21, ptr %a22
  %t23 = alloca i8, i64 2048, align 16
  store ptr %t23, ptr %a24
  store i64 0, ptr %a25
  br label %loop_cond26
loop_cond26:
  %t29 = load i64, ptr %a25
  %t30 = add i64 %t29, 1
  %t31 = load i64, ptr %a22
  %t32 = icmp slt i64 %t30, %t31
  br i1 %t32, label %loop_body27, label %loop_exit28
loop_body27:
  %t33 = call i64 @ax_rt_fork__seq()
  store i64 %t33, ptr %a34
  %t35 = load i64, ptr %a34
  %t36 = icmp eq i64 %t35, 0
  br i1 %t36, label %then38, label %else39
then38:
  %t41 = load i64, ptr %a1
  %t42 = load i64, ptr %a25
  %t43 = mul i64 %t41, %t42
  %t44 = load i64, ptr %a22
  %t45 = sdiv i64 %t43, %t44
  store i64 %t45, ptr %a46
  br label %loop_cond47
loop_cond47:
  %t50 = load i64, ptr %a46
  %t51 = load i64, ptr %a1
  %t52 = load i64, ptr %a25
  %t53 = add i64 %t52, 1
  %t54 = mul i64 %t51, %t53
  %t55 = load i64, ptr %a22
  %t56 = sdiv i64 %t54, %t55
  %t57 = icmp slt i64 %t50, %t56
  br i1 %t57, label %loop_body48, label %loop_exit49
loop_body48:
  %t58 = load ptr, ptr %a2
  %t59 = load ptr, ptr %a3
  %t60 = load i64, ptr %a46
  call void %t58(ptr %t59, i64 %t60)
  store i8 0, ptr %a61
  %t62 = load i64, ptr %a46
  %t63 = add i64 %t62, 1
  store i64 %t63, ptr %a46
  br label %loop_cond47
loop_exit49:
  %t64 = load i64, ptr %a46
  store i64 %t64, ptr %a65
  call void @ax_exit(i64 0)
  store i8 0, ptr %a66
  %t67 = load i64, ptr %a22
  store i64 %t67, ptr %a37
  br label %join40
else39:
  %t68 = load ptr, ptr %a24
  %t69 = load i64, ptr %a25
  %t70 = mul i64 %t69, 8
  %t71 = load i64, ptr %a34
  %t72 = getelementptr i8, ptr %t68, i64 %t70
  store i64 %t71, ptr %t72, align 1
  store i8 0, ptr %a73
  %t74 = load i64, ptr %a34
  %t75 = icmp slt i64 %t74, 0
  br i1 %t75, label %then77, label %else78
then77:
  %t80 = load i64, ptr %a1
  %t81 = load i64, ptr %a25
  %t82 = mul i64 %t80, %t81
  %t83 = load i64, ptr %a22
  %t84 = sdiv i64 %t82, %t83
  store i64 %t84, ptr %a85
  br label %loop_cond86
loop_cond86:
  %t89 = load i64, ptr %a85
  %t90 = load i64, ptr %a1
  %t91 = load i64, ptr %a25
  %t92 = add i64 %t91, 1
  %t93 = mul i64 %t90, %t92
  %t94 = load i64, ptr %a22
  %t95 = sdiv i64 %t93, %t94
  %t96 = icmp slt i64 %t89, %t95
  br i1 %t96, label %loop_body87, label %loop_exit88
loop_body87:
  %t97 = load ptr, ptr %a2
  %t98 = load ptr, ptr %a3
  %t99 = load i64, ptr %a85
  call void %t97(ptr %t98, i64 %t99)
  store i8 0, ptr %a100
  %t101 = load i64, ptr %a85
  %t102 = add i64 %t101, 1
  store i64 %t102, ptr %a85
  br label %loop_cond86
loop_exit88:
  %t103 = load i64, ptr %a85
  store i64 %t103, ptr %a104
  store i8 0, ptr %a76
  br label %join79
else78:
  store i8 0, ptr %a76
  br label %join79
join79:
  %t105 = load i8, ptr %a76
  store i8 %t105, ptr %a106
  %t107 = load i64, ptr %a25
  %t108 = add i64 %t107, 1
  store i64 %t108, ptr %a37
  br label %join40
join40:
  %t109 = load i64, ptr %a37
  store i64 %t109, ptr %a25
  br label %loop_cond26
loop_exit28:
  %t110 = load i64, ptr %a25
  store i64 %t110, ptr %a111
  %t112 = load i64, ptr %a1
  %t113 = load i64, ptr %a22
  %t114 = sub i64 %t113, 1
  %t115 = mul i64 %t112, %t114
  %t116 = load i64, ptr %a22
  %t117 = sdiv i64 %t115, %t116
  store i64 %t117, ptr %a118
  br label %loop_cond119
loop_cond119:
  %t122 = load i64, ptr %a118
  %t123 = load i64, ptr %a1
  %t124 = icmp slt i64 %t122, %t123
  br i1 %t124, label %loop_body120, label %loop_exit121
loop_body120:
  %t125 = load ptr, ptr %a2
  %t126 = load ptr, ptr %a3
  %t127 = load i64, ptr %a118
  call void %t125(ptr %t126, i64 %t127)
  store i8 0, ptr %a128
  %t129 = load i64, ptr %a118
  %t130 = add i64 %t129, 1
  store i64 %t130, ptr %a118
  br label %loop_cond119
loop_exit121:
  %t131 = load i64, ptr %a118
  store i64 %t131, ptr %a132
  store i64 0, ptr %a133
  br label %loop_cond134
loop_cond134:
  %t137 = load i64, ptr %a133
  %t138 = add i64 %t137, 1
  %t139 = load i64, ptr %a22
  %t140 = icmp slt i64 %t138, %t139
  br i1 %t140, label %loop_body135, label %loop_exit136
loop_body135:
  %t141 = load ptr, ptr %a24
  %t142 = load i64, ptr %a133
  %t143 = mul i64 %t142, 8
  %t144 = getelementptr i8, ptr %t141, i64 %t143
  %t145 = load i64, ptr %t144, align 1
  store i64 %t145, ptr %a146
  %t147 = load i64, ptr %a146
  %t148 = icmp sgt i64 %t147, 0
  br i1 %t148, label %then150, label %else151
then150:
  %t153 = load i64, ptr %a146
  %t154 = call i64 @ax_rt_wait__seq(i64 %t153)
  store i64 %t154, ptr %a149
  br label %join152
else151:
  store i64 0, ptr %a149
  br label %join152
join152:
  %t155 = load i64, ptr %a149
  store i64 %t155, ptr %a156
  %t157 = load i64, ptr %a156
  %t158 = icmp ne i64 %t157, 0
  br i1 %t158, label %then160, label %else161
then160:
  %t163 = insertvalue %ax_arr undef, ptr @.bytes.9, 0
  %t164 = insertvalue %ax_arr %t163, i64 23, 1
  %t165 = insertvalue %ax_arr %t164, i64 0, 2
  %t166 = extractvalue %ax_arr %t165, 0
  call void @ax_trap(ptr %t166)
  store i8 0, ptr %a159
  br label %join162
else161:
  store i8 0, ptr %a159
  br label %join162
join162:
  %t167 = load i8, ptr %a159
  store i8 %t167, ptr %a168
  %t169 = load i64, ptr %a133
  %t170 = add i64 %t169, 1
  store i64 %t170, ptr %a133
  br label %loop_cond134
loop_exit136:
  %t171 = load i64, ptr %a133
  store i64 %t171, ptr %a172
  store i8 0, ptr %a6
  br label %join9
join9:
  %t173 = load i8, ptr %a6
  ret void
}

; ax_usage  graph:7dd046804a179582
define void @ax_usage(ptr %p_program, ptr %p_names) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a7 = alloca i8
  %a9 = alloca i8
  %a14 = alloca i8
  %a16 = alloca i8
  store ptr %p_program, ptr %a1
  store ptr %p_names, ptr %a2
  %t3 = insertvalue %ax_arr undef, ptr @.bytes.10, 0
  %t4 = insertvalue %ax_arr %t3, i64 7, 1
  %t5 = insertvalue %ax_arr %t4, i64 0, 2
  %t6 = extractvalue %ax_arr %t5, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t6, i64 7)
  store i8 0, ptr %a7
  %t8 = load ptr, ptr %a1
  call void @ax_rt_puts__seq(i64 2, ptr %t8)
  store i8 0, ptr %a9
  %t10 = insertvalue %ax_arr undef, ptr @.bytes.11, 0
  %t11 = insertvalue %ax_arr %t10, i64 1, 1
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = extractvalue %ax_arr %t12, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t13, i64 1)
  store i8 0, ptr %a14
  %t15 = load ptr, ptr %a2
  call void @ax_rt_puts__seq(i64 2, ptr %t15)
  store i8 0, ptr %a16
  %t17 = insertvalue %ax_arr undef, ptr @.bytes.2, 0
  %t18 = insertvalue %ax_arr %t17, i64 1, 1
  %t19 = insertvalue %ax_arr %t18, i64 0, 2
  %t20 = extractvalue %ax_arr %t19, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t20, i64 1)
  ret void
}

; ax_precondition_failed  graph:08511977695e5ea4
define void @ax_precondition_failed(ptr %p_predicate) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a6 = alloca i8
  %a8 = alloca i8
  store ptr %p_predicate, ptr %a1
  %t2 = insertvalue %ax_arr undef, ptr @.bytes.12, 0
  %t3 = insertvalue %ax_arr %t2, i64 27, 1
  %t4 = insertvalue %ax_arr %t3, i64 0, 2
  %t5 = extractvalue %ax_arr %t4, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t5, i64 27)
  store i8 0, ptr %a6
  %t7 = load ptr, ptr %a1
  call void @ax_rt_puts__seq(i64 2, ptr %t7)
  store i8 0, ptr %a8
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.2, 0
  %t10 = insertvalue %ax_arr %t9, i64 1, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = extractvalue %ax_arr %t11, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t12, i64 1)
  ret void
}

; rt_format_integer  graph:050e9777048a5cdc
define internal i64 @ax_rt_format_integer__seq(ptr %p_buffer, i64 %p_end, i64 %p_value) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  %a3 = alloca i64
  %a6 = alloca i1
  %a8 = alloca i64
  %a16 = alloca i64
  %a18 = alloca i64
  %a20 = alloca i64
  %a21 = alloca i1
  %a36 = alloca i8
  %a42 = alloca i64
  %a44 = alloca i64
  %a52 = alloca i8
  store ptr %p_buffer, ptr %a1
  store i64 %p_end, ptr %a2
  store i64 %p_value, ptr %a3
  %t4 = load i64, ptr %a3
  %t5 = icmp slt i64 %t4, 0
  store i1 %t5, ptr %a6
  %t7 = load i1, ptr %a6
  br i1 %t7, label %then9, label %else10
then9:
  %t12 = load i64, ptr %a3
  store i64 %t12, ptr %a8
  br label %join11
else10:
  %t13 = load i64, ptr %a3
  %t14 = sub i64 0, %t13
  store i64 %t14, ptr %a8
  br label %join11
join11:
  %t15 = load i64, ptr %a8
  store i64 %t15, ptr %a16
  %t17 = load i64, ptr %a16
  store i64 %t17, ptr %a18
  %t19 = load i64, ptr %a2
  store i64 %t19, ptr %a20
  store i1 true, ptr %a21
  br label %loop_cond22
loop_cond22:
  %t25 = load i1, ptr %a21
  br i1 %t25, label %loop_body23, label %loop_exit24
loop_body23:
  %t26 = load i64, ptr %a18
  %t27 = sdiv i64 %t26, 10
  %t28 = load ptr, ptr %a1
  %t29 = load i64, ptr %a20
  %t30 = sub i64 %t29, 1
  %t31 = load i64, ptr %a18
  %t32 = srem i64 %t31, 10
  %t33 = sub i64 48, %t32
  %t34 = trunc i64 %t33 to i8
  %t35 = getelementptr i8, ptr %t28, i64 %t30
  store i8 %t34, ptr %t35, align 1
  store i8 0, ptr %a36
  %t37 = load i64, ptr %a20
  %t38 = sub i64 %t37, 1
  %t39 = load i64, ptr %a18
  %t40 = icmp sle i64 %t39, -10
  store i64 %t27, ptr %a18
  store i64 %t38, ptr %a20
  store i1 %t40, ptr %a21
  br label %loop_cond22
loop_exit24:
  %t41 = load i64, ptr %a20
  store i64 %t41, ptr %a42
  %t43 = load i1, ptr %a6
  br i1 %t43, label %then45, label %else46
then45:
  %t48 = load ptr, ptr %a1
  %t49 = load i64, ptr %a42
  %t50 = sub i64 %t49, 1
  %t51 = getelementptr i8, ptr %t48, i64 %t50
  store i8 45, ptr %t51, align 1
  store i8 0, ptr %a52
  %t53 = load i64, ptr %a42
  %t54 = sub i64 %t53, 1
  store i64 %t54, ptr %a44
  br label %join47
else46:
  %t55 = load i64, ptr %a42
  store i64 %t55, ptr %a44
  br label %join47
join47:
  %t56 = load i64, ptr %a44
  ret i64 %t56
}

; ax_print_i64  graph:2d3b1216c59324de
define void @ax_print_i64(i64 %p_v) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca ptr
  %a7 = alloca i64
  %a10 = alloca i8
  store i64 %p_v, ptr %a1
  %t2 = alloca i8, i64 64, align 16
  store ptr %t2, ptr %a3
  %t4 = load ptr, ptr %a3
  %t5 = load i64, ptr %a1
  %t6 = call i64 @ax_rt_format_integer__seq(ptr %t4, i64 63, i64 %t5)
  store i64 %t6, ptr %a7
  %t8 = load ptr, ptr %a3
  %t9 = getelementptr i8, ptr %t8, i64 63
  store i8 10, ptr %t9, align 1
  store i8 0, ptr %a10
  %t11 = load ptr, ptr %a3
  %t12 = load i64, ptr %a7
  %t13 = getelementptr i8, ptr %t11, i64 %t12
  %t14 = load i64, ptr %a7
  %t15 = sub i64 64, %t14
  call void @ax_rt_write_all__seq(i64 1, ptr %t13, i64 %t15)
  ret void
}

; rt_normalize_float  graph:cf97271b9caac432
define internal { double, i64 } @ax_rt_normalize_float__par(double %p_value) "no-builtins" {
entry:
  %a1 = alloca double
  %a3 = alloca double
  %a4 = alloca i64
  %a18 = alloca { double, i64 }
  %a21 = alloca double
  %a24 = alloca i64
  store double %p_value, ptr %a1
  %t2 = load double, ptr %a1
  store double %t2, ptr %a3
  store i64 0, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load double, ptr %a3
  %t9 = fcmp oge double %t8, 0x4024000000000000
  br i1 %t9, label %loop_body6, label %loop_exit7
loop_body6:
  %t10 = load double, ptr %a3
  %t11 = fdiv double %t10, 0x4024000000000000
  %t12 = load i64, ptr %a4
  %t13 = add i64 %t12, 1
  store double %t11, ptr %a3
  store i64 %t13, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t14 = load double, ptr %a3
  %t15 = insertvalue { double, i64 } undef, double %t14, 0
  %t16 = load i64, ptr %a4
  %t17 = insertvalue { double, i64 } %t15, i64 %t16, 1
  store { double, i64 } %t17, ptr %a18
  %t19 = load { double, i64 }, ptr %a18
  %t20 = extractvalue { double, i64 } %t19, 0
  store double %t20, ptr %a21
  %t22 = load { double, i64 }, ptr %a18
  %t23 = extractvalue { double, i64 } %t22, 1
  store i64 %t23, ptr %a24
  br label %loop_cond25
loop_cond25:
  %t28 = load double, ptr %a21
  %t29 = fcmp olt double %t28, 0x3FF0000000000000
  br i1 %t29, label %loop_body26, label %loop_exit27
loop_body26:
  %t30 = load double, ptr %a21
  %t31 = fmul double %t30, 0x4024000000000000
  %t32 = load i64, ptr %a24
  %t33 = sub i64 %t32, 1
  store double %t31, ptr %a21
  store i64 %t33, ptr %a24
  br label %loop_cond25
loop_exit27:
  %t34 = load double, ptr %a21
  %t35 = insertvalue { double, i64 } undef, double %t34, 0
  %t36 = load i64, ptr %a24
  %t37 = insertvalue { double, i64 } %t35, i64 %t36, 1
  ret { double, i64 } %t37
}

; rt_normalize_float  graph:cf97271b9caac432
define internal { double, i64 } @ax_rt_normalize_float__seq(double %p_value) "no-builtins" {
entry:
  %a1 = alloca double
  %a3 = alloca double
  %a4 = alloca i64
  %a18 = alloca { double, i64 }
  %a21 = alloca double
  %a24 = alloca i64
  store double %p_value, ptr %a1
  %t2 = load double, ptr %a1
  store double %t2, ptr %a3
  store i64 0, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load double, ptr %a3
  %t9 = fcmp oge double %t8, 0x4024000000000000
  br i1 %t9, label %loop_body6, label %loop_exit7
loop_body6:
  %t10 = load double, ptr %a3
  %t11 = fdiv double %t10, 0x4024000000000000
  %t12 = load i64, ptr %a4
  %t13 = add i64 %t12, 1
  store double %t11, ptr %a3
  store i64 %t13, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t14 = load double, ptr %a3
  %t15 = insertvalue { double, i64 } undef, double %t14, 0
  %t16 = load i64, ptr %a4
  %t17 = insertvalue { double, i64 } %t15, i64 %t16, 1
  store { double, i64 } %t17, ptr %a18
  %t19 = load { double, i64 }, ptr %a18
  %t20 = extractvalue { double, i64 } %t19, 0
  store double %t20, ptr %a21
  %t22 = load { double, i64 }, ptr %a18
  %t23 = extractvalue { double, i64 } %t22, 1
  store i64 %t23, ptr %a24
  br label %loop_cond25
loop_cond25:
  %t28 = load double, ptr %a21
  %t29 = fcmp olt double %t28, 0x3FF0000000000000
  br i1 %t29, label %loop_body26, label %loop_exit27
loop_body26:
  %t30 = load double, ptr %a21
  %t31 = fmul double %t30, 0x4024000000000000
  %t32 = load i64, ptr %a24
  %t33 = sub i64 %t32, 1
  store double %t31, ptr %a21
  store i64 %t33, ptr %a24
  br label %loop_cond25
loop_exit27:
  %t34 = load double, ptr %a21
  %t35 = insertvalue { double, i64 } undef, double %t34, 0
  %t36 = load i64, ptr %a24
  %t37 = insertvalue { double, i64 } %t35, i64 %t36, 1
  ret { double, i64 } %t37
}

; ax_print_f64  graph:236580e8bd6279c6
define void @ax_print_f64(double %p_v) "no-builtins" {
entry:
  %a1 = alloca double
  %a5 = alloca i8
  %a16 = alloca i1
  %a18 = alloca double
  %a26 = alloca double
  %a29 = alloca i8
  %a34 = alloca i8
  %a51 = alloca i8
  %a56 = alloca i8
  %a71 = alloca { double, i64 }
  %a77 = alloca i64
  %a80 = alloca i64
  %a88 = alloca i64
  %a93 = alloca i64
  %a99 = alloca i64
  %a101 = alloca ptr
  %a103 = alloca i64
  %a109 = alloca i8
  %a111 = alloca i64
  %a116 = alloca i8
  %a117 = alloca i64
  %a118 = alloca i64
  %a128 = alloca i64
  %a143 = alloca i8
  %a148 = alloca i64
  %a156 = alloca i64
  %a161 = alloca i8
  %a165 = alloca i8
  %a169 = alloca i64
  %a172 = alloca i8
  store double %p_v, ptr %a1
  %t2 = load double, ptr %a1
  %t3 = load double, ptr %a1
  %t4 = fcmp une double %t2, %t3
  br i1 %t4, label %then6, label %else7
then6:
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.13, 0
  %t10 = insertvalue %ax_arr %t9, i64 4, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = extractvalue %ax_arr %t11, 0
  call void @ax_rt_write_all__seq(i64 1, ptr %t12, i64 4)
  store i8 0, ptr %a5
  br label %join8
else7:
  %t13 = load double, ptr %a1
  %t14 = bitcast double %t13 to i64
  %t15 = icmp slt i64 %t14, 0
  store i1 %t15, ptr %a16
  %t17 = load i1, ptr %a16
  br i1 %t17, label %then19, label %else20
then19:
  %t22 = load double, ptr %a1
  %t23 = fsub double 0x0000000000000000, %t22
  store double %t23, ptr %a18
  br label %join21
else20:
  %t24 = load double, ptr %a1
  store double %t24, ptr %a18
  br label %join21
join21:
  %t25 = load double, ptr %a18
  store double %t25, ptr %a26
  %t27 = load double, ptr %a26
  %t28 = fcmp oeq double %t27, 0x0000000000000000
  br i1 %t28, label %then30, label %else31
then30:
  %t33 = load i1, ptr %a16
  br i1 %t33, label %then35, label %else36
then35:
  %t38 = insertvalue %ax_arr undef, ptr @.bytes.14, 0
  %t39 = insertvalue %ax_arr %t38, i64 3, 1
  %t40 = insertvalue %ax_arr %t39, i64 0, 2
  %t41 = extractvalue %ax_arr %t40, 0
  call void @ax_rt_write_all__seq(i64 1, ptr %t41, i64 3)
  store i8 0, ptr %a34
  br label %join37
else36:
  %t42 = insertvalue %ax_arr undef, ptr @.bytes.15, 0
  %t43 = insertvalue %ax_arr %t42, i64 2, 1
  %t44 = insertvalue %ax_arr %t43, i64 0, 2
  %t45 = extractvalue %ax_arr %t44, 0
  call void @ax_rt_write_all__seq(i64 1, ptr %t45, i64 2)
  store i8 0, ptr %a34
  br label %join37
join37:
  %t46 = load i8, ptr %a34
  store i8 %t46, ptr %a29
  br label %join32
else31:
  %t47 = load double, ptr %a26
  %t48 = fdiv double %t47, 0x4000000000000000
  %t49 = load double, ptr %a26
  %t50 = fcmp oeq double %t48, %t49
  br i1 %t50, label %then52, label %else53
then52:
  %t55 = load i1, ptr %a16
  br i1 %t55, label %then57, label %else58
then57:
  %t60 = insertvalue %ax_arr undef, ptr @.bytes.16, 0
  %t61 = insertvalue %ax_arr %t60, i64 5, 1
  %t62 = insertvalue %ax_arr %t61, i64 0, 2
  %t63 = extractvalue %ax_arr %t62, 0
  call void @ax_rt_write_all__seq(i64 1, ptr %t63, i64 5)
  store i8 0, ptr %a56
  br label %join59
else58:
  %t64 = insertvalue %ax_arr undef, ptr @.bytes.17, 0
  %t65 = insertvalue %ax_arr %t64, i64 4, 1
  %t66 = insertvalue %ax_arr %t65, i64 0, 2
  %t67 = extractvalue %ax_arr %t66, 0
  call void @ax_rt_write_all__seq(i64 1, ptr %t67, i64 4)
  store i8 0, ptr %a56
  br label %join59
join59:
  %t68 = load i8, ptr %a56
  store i8 %t68, ptr %a51
  br label %join54
else53:
  %t69 = load double, ptr %a26
  %t70 = call { double, i64 } @ax_rt_normalize_float__seq(double %t69)
  store { double, i64 } %t70, ptr %a71
  %t72 = load { double, i64 }, ptr %a71
  %t73 = extractvalue { double, i64 } %t72, 0
  %t74 = fmul double %t73, 0x4341C37937E08000
  %t75 = fadd double %t74, 0x3FE0000000000000
  %t76 = fptosi double %t75 to i64
  store i64 %t76, ptr %a77
  %t78 = load i64, ptr %a77
  %t79 = icmp sge i64 %t78, 100000000000000000
  br i1 %t79, label %then81, label %else82
then81:
  %t84 = load i64, ptr %a77
  %t85 = sdiv i64 %t84, 10
  store i64 %t85, ptr %a80
  br label %join83
else82:
  %t86 = load i64, ptr %a77
  store i64 %t86, ptr %a80
  br label %join83
join83:
  %t87 = load i64, ptr %a80
  store i64 %t87, ptr %a88
  %t89 = load { double, i64 }, ptr %a71
  %t90 = extractvalue { double, i64 } %t89, 1
  %t91 = load i64, ptr %a77
  %t92 = icmp sge i64 %t91, 100000000000000000
  br i1 %t92, label %then94, label %else95
then94:
  store i64 1, ptr %a93
  br label %join96
else95:
  store i64 0, ptr %a93
  br label %join96
join96:
  %t97 = load i64, ptr %a93
  %t98 = add i64 %t90, %t97
  store i64 %t98, ptr %a99
  %t100 = alloca i8, i64 128, align 16
  store ptr %t100, ptr %a101
  %t102 = load i1, ptr %a16
  br i1 %t102, label %then104, label %else105
then104:
  %t107 = load ptr, ptr %a101
  %t108 = getelementptr i8, ptr %t107, i64 0
  store i8 45, ptr %t108, align 1
  store i8 0, ptr %a109
  store i64 1, ptr %a103
  br label %join106
else105:
  store i64 0, ptr %a103
  br label %join106
join106:
  %t110 = load i64, ptr %a103
  store i64 %t110, ptr %a111
  %t112 = load ptr, ptr %a101
  %t113 = load i64, ptr %a111
  %t114 = add i64 %t113, 1
  %t115 = getelementptr i8, ptr %t112, i64 %t114
  store i8 46, ptr %t115, align 1
  store i8 0, ptr %a116
  store i64 0, ptr %a117
  store i64 10000000000000000, ptr %a118
  br label %loop_cond119
loop_cond119:
  %t122 = load i64, ptr %a117
  %t123 = icmp slt i64 %t122, 17
  br i1 %t123, label %loop_body120, label %loop_exit121
loop_body120:
  %t124 = load ptr, ptr %a101
  %t125 = load i64, ptr %a111
  %t126 = load i64, ptr %a117
  %t127 = icmp eq i64 %t126, 0
  br i1 %t127, label %then129, label %else130
then129:
  store i64 0, ptr %a128
  br label %join131
else130:
  %t132 = load i64, ptr %a117
  %t133 = add i64 %t132, 1
  store i64 %t133, ptr %a128
  br label %join131
join131:
  %t134 = load i64, ptr %a128
  %t135 = add i64 %t125, %t134
  %t136 = load i64, ptr %a88
  %t137 = load i64, ptr %a118
  %t138 = sdiv i64 %t136, %t137
  %t139 = srem i64 %t138, 10
  %t140 = add i64 48, %t139
  %t141 = trunc i64 %t140 to i8
  %t142 = getelementptr i8, ptr %t124, i64 %t135
  store i8 %t141, ptr %t142, align 1
  store i8 0, ptr %a143
  %t144 = load i64, ptr %a117
  %t145 = add i64 %t144, 1
  %t146 = load i64, ptr %a118
  %t147 = icmp sge i64 %t146, 10
  br i1 %t147, label %then149, label %else150
then149:
  %t152 = load i64, ptr %a118
  %t153 = sdiv i64 %t152, 10
  store i64 %t153, ptr %a148
  br label %join151
else150:
  store i64 1, ptr %a148
  br label %join151
join151:
  %t154 = load i64, ptr %a148
  store i64 %t145, ptr %a117
  store i64 %t154, ptr %a118
  br label %loop_cond119
loop_exit121:
  %t155 = load i64, ptr %a117
  store i64 %t155, ptr %a156
  %t157 = load ptr, ptr %a101
  %t158 = load i64, ptr %a111
  %t159 = add i64 %t158, 18
  %t160 = getelementptr i8, ptr %t157, i64 %t159
  store i8 101, ptr %t160, align 1
  store i8 0, ptr %a161
  %t162 = load ptr, ptr %a101
  %t163 = load i64, ptr %a111
  %t164 = add i64 %t163, 19
  call void @ax_rt_write_all__seq(i64 1, ptr %t162, i64 %t164)
  store i8 0, ptr %a165
  %t166 = load ptr, ptr %a101
  %t167 = load i64, ptr %a99
  %t168 = call i64 @ax_rt_format_integer__seq(ptr %t166, i64 127, i64 %t167)
  store i64 %t168, ptr %a169
  %t170 = load ptr, ptr %a101
  %t171 = getelementptr i8, ptr %t170, i64 127
  store i8 10, ptr %t171, align 1
  store i8 0, ptr %a172
  %t173 = load ptr, ptr %a101
  %t174 = load i64, ptr %a169
  %t175 = getelementptr i8, ptr %t173, i64 %t174
  %t176 = load i64, ptr %a169
  %t177 = sub i64 128, %t176
  call void @ax_rt_write_all__seq(i64 1, ptr %t175, i64 %t177)
  store i8 0, ptr %a51
  br label %join54
join54:
  %t178 = load i8, ptr %a51
  store i8 %t178, ptr %a29
  br label %join32
join32:
  %t179 = load i8, ptr %a29
  store i8 %t179, ptr %a5
  br label %join8
join8:
  %t180 = load i8, ptr %a5
  ret void
}

; ax_print_bytes  graph:d67fd7259993dd9e
define void @ax_print_bytes(ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  store ptr %p_p, ptr %a1
  store i64 %p_n, ptr %a2
  %t3 = load ptr, ptr %a1
  %t4 = load i64, ptr %a2
  call void @ax_rt_write_all__seq(i64 1, ptr %t3, i64 %t4)
  ret void
}

; rt_retry  graph:221e83363228ee18
define internal i1 @ax_rt_retry__seq() "no-builtins" {
entry:
  %a5 = alloca i64
  %a8 = alloca i1
  %t1 = call ptr @ax_rt_errno__seq()
  %t2 = getelementptr i8, ptr %t1, i64 0
  %t3 = load i32, ptr %t2, align 1
  %t4 = sext i32 %t3 to i64
  store i64 %t4, ptr %a5
  %t6 = load i64, ptr %a5
  %t7 = icmp eq i64 %t6, 4
  store i1 %t7, ptr %a8
  br i1 %t7, label %join10, label %rhs9
rhs9:
  %t11 = load i64, ptr %a5
  %t12 = call i64 @ax_rt_again__seq()
  %t13 = icmp eq i64 %t11, %t12
  store i1 %t13, ptr %a8
  br label %join10
join10:
  %t14 = load i1, ptr %a8
  ret i1 %t14
}

; rt_nonblock  graph:1d9b8b8624e43dd9
define internal i64 @ax_rt_nonblock__seq(i64 %p_fd) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca i64
  %a7 = alloca i64
  %a17 = alloca i64
  store i64 %p_fd, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 @ax_rt_fcntl__seq(i64 %t2, i64 3, i64 0)
  store i64 %t3, ptr %a4
  %t5 = load i64, ptr %a4
  %t6 = icmp slt i64 %t5, 0
  br i1 %t6, label %then8, label %else9
then8:
  store i64 -1, ptr %a7
  br label %join10
else9:
  %t11 = load i64, ptr %a1
  %t12 = load i64, ptr %a4
  %t13 = call i64 @ax_rt_nonblock_flag__seq()
  %t14 = sdiv i64 %t12, %t13
  %t15 = srem i64 %t14, 2
  %t16 = icmp eq i64 %t15, 1
  br i1 %t16, label %then18, label %else19
then18:
  %t21 = load i64, ptr %a4
  store i64 %t21, ptr %a17
  br label %join20
else19:
  %t22 = load i64, ptr %a4
  %t23 = call i64 @ax_rt_nonblock_flag__seq()
  %t24 = add i64 %t22, %t23
  store i64 %t24, ptr %a17
  br label %join20
join20:
  %t25 = load i64, ptr %a17
  %t26 = call i64 @ax_rt_fcntl__seq(i64 %t11, i64 4, i64 %t25)
  store i64 %t26, ptr %a7
  br label %join10
join10:
  %t27 = load i64, ptr %a7
  ret i64 %t27
}

; rt_listener  graph:e2e50ab909221650
define internal i64 @ax_rt_listener__seq(i64 %p_port) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca i64
  %a6 = alloca i64
  %a14 = alloca i8
  %a16 = alloca ptr
  %a20 = alloca ptr
  %a22 = alloca i8
  %a28 = alloca i8
  %a34 = alloca i8
  %a38 = alloca i8
  %a45 = alloca i64
  %a49 = alloca i64
  %a52 = alloca i1
  %a59 = alloca i1
  %a66 = alloca i64
  %a72 = alloca i64
  %a77 = alloca i8
  store i64 %p_port, ptr %a1
  %t2 = call i64 @ax_rt_socket__seq(i64 2, i64 1, i64 0)
  store i64 %t2, ptr %a3
  %t4 = load i64, ptr %a3
  %t5 = icmp slt i64 %t4, 0
  br i1 %t5, label %then7, label %else8
then7:
  %t10 = insertvalue %ax_arr undef, ptr @.bytes.18, 0
  %t11 = insertvalue %ax_arr %t10, i64 14, 1
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = extractvalue %ax_arr %t12, 0
  call void @ax_trap(ptr %t13)
  store i8 0, ptr %a14
  store i64 -1, ptr %a6
  br label %join9
else8:
  %t15 = alloca i8, i64 32, align 16
  store ptr %t15, ptr %a16
  %t17 = load ptr, ptr %a16
  %t18 = trunc i64 0 to i32
  %t19 = call ptr @memset(ptr %t17, i32 %t18, i64 32)
  store ptr %t19, ptr %a20
  %t21 = load ptr, ptr %a16
  call void @ax_rt_address__seq(ptr %t21)
  store i8 0, ptr %a22
  %t23 = load ptr, ptr %a16
  %t24 = load i64, ptr %a1
  %t25 = sdiv i64 %t24, 256
  %t26 = trunc i64 %t25 to i8
  %t27 = getelementptr i8, ptr %t23, i64 2
  store i8 %t26, ptr %t27, align 1
  store i8 0, ptr %a28
  %t29 = load ptr, ptr %a16
  %t30 = load i64, ptr %a1
  %t31 = srem i64 %t30, 256
  %t32 = trunc i64 %t31 to i8
  %t33 = getelementptr i8, ptr %t29, i64 3
  store i8 %t32, ptr %t33, align 1
  store i8 0, ptr %a34
  %t35 = load ptr, ptr %a16
  %t36 = trunc i64 1 to i32
  %t37 = getelementptr i8, ptr %t35, i64 16
  store i32 %t36, ptr %t37, align 1
  store i8 0, ptr %a38
  %t39 = load i64, ptr %a3
  %t40 = call i64 @ax_rt_socket_level__seq()
  %t41 = call i64 @ax_rt_reuseaddr__seq()
  %t42 = load ptr, ptr %a16
  %t43 = getelementptr i8, ptr %t42, i64 16
  %t44 = call i64 @ax_rt_setsockopt__seq(i64 %t39, i64 %t40, i64 %t41, ptr %t43, i64 4)
  store i64 %t44, ptr %a45
  %t46 = load i64, ptr %a3
  %t47 = load ptr, ptr %a16
  %t48 = call i64 @ax_rt_bind__seq(i64 %t46, ptr %t47, i64 16)
  store i64 %t48, ptr %a49
  %t50 = load i64, ptr %a49
  %t51 = icmp slt i64 %t50, 0
  store i1 %t51, ptr %a52
  br i1 %t51, label %join54, label %rhs53
rhs53:
  %t55 = load i64, ptr %a3
  %t56 = call i64 @ax_rt_listen__seq(i64 %t55, i64 4096)
  %t57 = icmp slt i64 %t56, 0
  store i1 %t57, ptr %a52
  br label %join54
join54:
  %t58 = load i1, ptr %a52
  store i1 %t58, ptr %a59
  br i1 %t58, label %join61, label %rhs60
rhs60:
  %t62 = load i64, ptr %a3
  %t63 = call i64 @ax_rt_nonblock__seq(i64 %t62)
  %t64 = icmp slt i64 %t63, 0
  store i1 %t64, ptr %a59
  br label %join61
join61:
  %t65 = load i1, ptr %a59
  br i1 %t65, label %then67, label %else68
then67:
  %t70 = load i64, ptr %a3
  %t71 = call i64 @ax_rt_close__seq(i64 %t70)
  store i64 %t71, ptr %a72
  %t73 = insertvalue %ax_arr undef, ptr @.bytes.19, 0
  %t74 = insertvalue %ax_arr %t73, i64 19, 1
  %t75 = insertvalue %ax_arr %t74, i64 0, 2
  %t76 = extractvalue %ax_arr %t75, 0
  call void @ax_trap(ptr %t76)
  store i8 0, ptr %a77
  store i64 -1, ptr %a66
  br label %join69
else68:
  %t78 = load i64, ptr %a3
  store i64 %t78, ptr %a66
  br label %join69
join69:
  %t79 = load i64, ptr %a66
  store i64 %t79, ptr %a6
  br label %join9
join9:
  %t80 = load i64, ptr %a6
  ret i64 %t80
}

; rt_read  graph:8ac8d6d721d38af7
define internal i64 @ax_rt_read__seq(i64 %p_fd, ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca i64
  store i64 %p_fd, ptr %a1
  store ptr %p_p, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load ptr, ptr %a2
  %t6 = ptrtoint ptr %t5 to i64
  %t7 = load i64, ptr %a3
  %t8 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t6, i64 %t7, i64 0, i64 0, i64 0, i64 63)
  %t9 = call i64 @ax_rt_result__seq(i64 %t8)
  ret i64 %t9
}

; rt_write  graph:5191c9dcd57964c0
define internal i64 @ax_rt_write__seq(i64 %p_fd, ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca i64
  store i64 %p_fd, ptr %a1
  store ptr %p_p, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load ptr, ptr %a2
  %t6 = ptrtoint ptr %t5 to i64
  %t7 = load i64, ptr %a3
  %t8 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t6, i64 %t7, i64 0, i64 0, i64 0, i64 64)
  %t9 = call i64 @ax_rt_result__seq(i64 %t8)
  ret i64 %t9
}

; rt_close  graph:67396d428fa38ea2
define internal i64 @ax_rt_close__seq(i64 %p_fd) "no-builtins" {
entry:
  %a1 = alloca i64
  store i64 %p_fd, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t2, i64 0, i64 0, i64 0, i64 0, i64 0, i64 57)
  %t4 = call i64 @ax_rt_result__seq(i64 %t3)
  ret i64 %t4
}

; ax_exit  graph:8ff237943d83f628
define void @ax_exit(i64 %p_status) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca i64
  store i64 %p_status, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t2, i64 0, i64 0, i64 0, i64 0, i64 0, i64 94)
  store i64 %t3, ptr %a4
  ret void
}

; rt_mmap  graph:6a5c1ad199f8bad8
define internal i64 @ax_rt_mmap__seq(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  store i64 %p_n, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 0, i64 %t2, i64 3, i64 33, i64 -1, i64 0, i64 222)
  ret i64 %t3
}

; rt_munmap  graph:4fcd110e8a3fb0d8
define internal i64 @ax_rt_munmap__seq(ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  store ptr %p_p, ptr %a1
  store i64 %p_n, ptr %a2
  %t3 = load ptr, ptr %a1
  %t4 = ptrtoint ptr %t3 to i64
  %t5 = load i64, ptr %a2
  %t6 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t5, i64 0, i64 0, i64 0, i64 0, i64 215)
  ret i64 %t6
}

; rt_getpid  graph:1d65cd8c130fcddd
define internal i64 @ax_rt_getpid__seq() "no-builtins" {
entry:
  %t1 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i64 172)
  ret i64 %t1
}

; rt_getppid  graph:f3c5e9a78f633fbf
define internal i64 @ax_rt_getppid__seq() "no-builtins" {
entry:
  %t1 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i64 173)
  ret i64 %t1
}

; rt_socket  graph:a005d6f11688fb17
define internal i64 @ax_rt_socket__seq(i64 %p_domain, i64 %p_kind, i64 %p_protocol) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  store i64 %p_domain, ptr %a1
  store i64 %p_kind, ptr %a2
  store i64 %p_protocol, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load i64, ptr %a2
  %t6 = load i64, ptr %a3
  %t7 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t5, i64 %t6, i64 0, i64 0, i64 0, i64 198)
  %t8 = call i64 @ax_rt_result__seq(i64 %t7)
  ret i64 %t8
}

; rt_setsockopt  graph:ecebf9bb4c281b4f
define internal i64 @ax_rt_setsockopt__seq(i64 %p_fd, i64 %p_level, i64 %p_option, ptr %p_value, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  %a4 = alloca ptr
  %a5 = alloca i64
  store i64 %p_fd, ptr %a1
  store i64 %p_level, ptr %a2
  store i64 %p_option, ptr %a3
  store ptr %p_value, ptr %a4
  store i64 %p_n, ptr %a5
  %t6 = load i64, ptr %a1
  %t7 = load i64, ptr %a2
  %t8 = load i64, ptr %a3
  %t9 = load ptr, ptr %a4
  %t10 = ptrtoint ptr %t9 to i64
  %t11 = load i64, ptr %a5
  %t12 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t6, i64 %t7, i64 %t8, i64 %t10, i64 %t11, i64 0, i64 208)
  %t13 = call i64 @ax_rt_result__seq(i64 %t12)
  ret i64 %t13
}

; rt_bind  graph:0cb2b50a79e52d98
define internal i64 @ax_rt_bind__seq(i64 %p_fd, ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca i64
  store i64 %p_fd, ptr %a1
  store ptr %p_p, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load ptr, ptr %a2
  %t6 = ptrtoint ptr %t5 to i64
  %t7 = load i64, ptr %a3
  %t8 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t6, i64 %t7, i64 0, i64 0, i64 0, i64 200)
  %t9 = call i64 @ax_rt_result__seq(i64 %t8)
  ret i64 %t9
}

; rt_listen  graph:7580db8cc6ec8a66
define internal i64 @ax_rt_listen__seq(i64 %p_fd, i64 %p_backlog) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  store i64 %p_fd, ptr %a1
  store i64 %p_backlog, ptr %a2
  %t3 = load i64, ptr %a1
  %t4 = load i64, ptr %a2
  %t5 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t3, i64 %t4, i64 0, i64 0, i64 0, i64 0, i64 201)
  %t6 = call i64 @ax_rt_result__seq(i64 %t5)
  ret i64 %t6
}

; rt_accept_fd  graph:8b911ff24cd47569
define internal i64 @ax_rt_accept_fd__seq(i64 %p_fd) "no-builtins" {
entry:
  %a1 = alloca i64
  store i64 %p_fd, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t2, i64 0, i64 0, i64 0, i64 0, i64 0, i64 202)
  %t4 = call i64 @ax_rt_result__seq(i64 %t3)
  ret i64 %t4
}

; rt_fcntl  graph:41cc16504a33b3d9
define internal i64 @ax_rt_fcntl__seq(i64 %p_fd, i64 %p_command, i64 %p_arg) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  store i64 %p_fd, ptr %a1
  store i64 %p_command, ptr %a2
  store i64 %p_arg, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load i64, ptr %a2
  %t6 = load i64, ptr %a3
  %t7 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t5, i64 %t6, i64 0, i64 0, i64 0, i64 25)
  %t8 = call i64 @ax_rt_result__seq(i64 %t7)
  ret i64 %t8
}

; rt_send  graph:92e1448751fb86d8
define internal i64 @ax_rt_send__seq(i64 %p_fd, ptr %p_p, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca i64
  store i64 %p_fd, ptr %a1
  store ptr %p_p, ptr %a2
  store i64 %p_n, ptr %a3
  %t4 = load i64, ptr %a1
  %t5 = load ptr, ptr %a2
  %t6 = ptrtoint ptr %t5 to i64
  %t7 = load i64, ptr %a3
  %t8 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t4, i64 %t6, i64 %t7, i64 16384, i64 0, i64 0, i64 206)
  %t9 = call i64 @ax_rt_result__seq(i64 %t8)
  ret i64 %t9
}

; rt_poll  graph:8251e4329adf6bf7
define internal i64 @ax_rt_poll__seq(ptr %p_fds, i64 %p_count) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  %a4 = alloca ptr
  %a7 = alloca i8
  %a10 = alloca i8
  store ptr %p_fds, ptr %a1
  store i64 %p_count, ptr %a2
  %t3 = alloca i8, i64 16, align 16
  store ptr %t3, ptr %a4
  %t5 = load ptr, ptr %a4
  %t6 = getelementptr i8, ptr %t5, i64 0
  store i64 1, ptr %t6, align 1
  store i8 0, ptr %a7
  %t8 = load ptr, ptr %a4
  %t9 = getelementptr i8, ptr %t8, i64 8
  store i64 0, ptr %t9, align 1
  store i8 0, ptr %a10
  %t11 = load ptr, ptr %a1
  %t12 = ptrtoint ptr %t11 to i64
  %t13 = load i64, ptr %a2
  %t14 = load ptr, ptr %a4
  %t15 = ptrtoint ptr %t14 to i64
  %t16 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t12, i64 %t13, i64 %t15, i64 0, i64 0, i64 0, i64 73)
  %t17 = call i64 @ax_rt_result__seq(i64 %t16)
  ret i64 %t17
}

; rt_epoll_create  graph:4c47f62e14c05671
define internal i64 @ax_rt_epoll_create__seq() "no-builtins" {
entry:
  %t1 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 524288, i64 0, i64 0, i64 0, i64 0, i64 0, i64 20)
  %t2 = call i64 @ax_rt_result__seq(i64 %t1)
  ret i64 %t2
}

; rt_epoll_ctl  graph:25603e6b9fb438f9
define internal i64 @ax_rt_epoll_ctl__seq(i64 %p_epfd, i64 %p_op, i64 %p_fd, i64 %p_mask, i64 %p_token) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i64
  %a7 = alloca ptr
  %a11 = alloca i8
  %a15 = alloca i8
  store i64 %p_epfd, ptr %a1
  store i64 %p_op, ptr %a2
  store i64 %p_fd, ptr %a3
  store i64 %p_mask, ptr %a4
  store i64 %p_token, ptr %a5
  %t6 = alloca i8, i64 16, align 16
  store ptr %t6, ptr %a7
  %t8 = load ptr, ptr %a7
  %t9 = load i64, ptr %a4
  %t10 = getelementptr i8, ptr %t8, i64 0
  store i64 %t9, ptr %t10, align 1
  store i8 0, ptr %a11
  %t12 = load ptr, ptr %a7
  %t13 = load i64, ptr %a5
  %t14 = getelementptr i8, ptr %t12, i64 8
  store i64 %t13, ptr %t14, align 1
  store i8 0, ptr %a15
  %t16 = load i64, ptr %a1
  %t17 = load i64, ptr %a2
  %t18 = load i64, ptr %a3
  %t19 = load ptr, ptr %a7
  %t20 = ptrtoint ptr %t19 to i64
  %t21 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t16, i64 %t17, i64 %t18, i64 %t20, i64 0, i64 0, i64 21)
  %t22 = call i64 @ax_rt_result__seq(i64 %t21)
  ret i64 %t22
}

; rt_epoll_wait  graph:504b4154805df733
define internal i64 @ax_rt_epoll_wait__seq(i64 %p_epfd, ptr %p_events) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  store i64 %p_epfd, ptr %a1
  store ptr %p_events, ptr %a2
  %t3 = load i64, ptr %a1
  %t4 = load ptr, ptr %a2
  %t5 = ptrtoint ptr %t4 to i64
  %t6 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t3, i64 %t5, i64 1026, i64 1000, i64 0, i64 8, i64 22)
  %t7 = call i64 @ax_rt_result__seq(i64 %t6)
  ret i64 %t7
}

; rt_socketpair  graph:b47e44006b2910ef
define internal i64 @ax_rt_socketpair__seq(ptr %p_p) "no-builtins" {
entry:
  %a1 = alloca ptr
  store ptr %p_p, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = ptrtoint ptr %t2 to i64
  %t4 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 1, i64 1, i64 0, i64 %t3, i64 0, i64 0, i64 199)
  %t5 = call i64 @ax_rt_result__seq(i64 %t4)
  ret i64 %t5
}

; rt_wait  graph:0164b888effac40c
define internal i64 @ax_rt_wait__seq(i64 %p_pid) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca ptr
  %a6 = alloca i8
  %a7 = alloca i64
  %a8 = alloca i1
  %a18 = alloca i64
  %a22 = alloca i8
  %a29 = alloca i1
  %a38 = alloca i64
  %a41 = alloca i64
  store i64 %p_pid, ptr %a1
  %t2 = alloca i8, i64 24, align 16
  store ptr %t2, ptr %a3
  %t4 = load ptr, ptr %a3
  %t5 = getelementptr i8, ptr %t4, i64 0
  store i64 0, ptr %t5, align 1
  store i8 0, ptr %a6
  store i64 -1, ptr %a7
  store i1 true, ptr %a8
  br label %loop_cond9
loop_cond9:
  %t12 = load i1, ptr %a8
  br i1 %t12, label %loop_body10, label %loop_exit11
loop_body10:
  %t13 = load i64, ptr %a1
  %t14 = load ptr, ptr %a3
  %t15 = ptrtoint ptr %t14 to i64
  %t16 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 %t13, i64 %t15, i64 0, i64 0, i64 0, i64 0, i64 260)
  %t17 = call i64 @ax_rt_result__seq(i64 %t16)
  store i64 %t17, ptr %a18
  %t19 = load ptr, ptr %a3
  %t20 = load i64, ptr %a18
  %t21 = getelementptr i8, ptr %t19, i64 16
  store i64 %t20, ptr %t21, align 1
  store i8 0, ptr %a22
  %t23 = load i64, ptr %a18
  %t24 = call ptr @ax_rt_errno__seq()
  %t25 = getelementptr i8, ptr %t24, i64 0
  %t26 = load i32, ptr %t25, align 1
  %t27 = trunc i64 4 to i32
  %t28 = icmp eq i32 %t26, %t27
  store i1 %t28, ptr %a29
  br i1 %t28, label %rhs30, label %join31
rhs30:
  %t32 = load ptr, ptr %a3
  %t33 = getelementptr i8, ptr %t32, i64 16
  %t34 = load i64, ptr %t33, align 1
  %t35 = icmp slt i64 %t34, 0
  store i1 %t35, ptr %a29
  br label %join31
join31:
  %t36 = load i1, ptr %a29
  store i64 %t23, ptr %a7
  store i1 %t36, ptr %a8
  br label %loop_cond9
loop_exit11:
  %t37 = load i64, ptr %a7
  store i64 %t37, ptr %a38
  %t39 = load i64, ptr %a38
  %t40 = icmp slt i64 %t39, 0
  br i1 %t40, label %then42, label %else43
then42:
  store i64 1, ptr %a41
  br label %join44
else43:
  %t45 = load ptr, ptr %a3
  %t46 = getelementptr i8, ptr %t45, i64 0
  %t47 = load i32, ptr %t46, align 1
  %t48 = sext i32 %t47 to i64
  store i64 %t48, ptr %a41
  br label %join44
join44:
  %t49 = load i64, ptr %a41
  ret i64 %t49
}

; rt_ncpu  graph:1e58802b54c332f3
define internal i64 @ax_rt_ncpu__seq() "no-builtins" {
entry:
  %a3 = alloca i64
  %a6 = alloca i64
  %a12 = alloca ptr
  %a16 = alloca ptr
  %a20 = alloca i64
  %a21 = alloca i64
  %a22 = alloca i64
  %a36 = alloca i64
  %a37 = alloca i64
  %a52 = alloca i64
  %a55 = alloca i1
  %a61 = alloca i64
  %a67 = alloca i64
  %a70 = alloca i8
  %t1 = getelementptr i8, ptr @ax_runtime_state, i64 16
  %t2 = load i64, ptr %t1, align 1
  store i64 %t2, ptr %a3
  %t4 = load i64, ptr %a3
  %t5 = icmp sgt i64 %t4, 0
  br i1 %t5, label %then7, label %else8
then7:
  %t10 = load i64, ptr %a3
  store i64 %t10, ptr %a6
  br label %join9
else8:
  %t11 = alloca i8, i64 128, align 16
  store ptr %t11, ptr %a12
  %t13 = load ptr, ptr %a12
  %t14 = trunc i64 0 to i32
  %t15 = call ptr @memset(ptr %t13, i32 %t14, i64 128)
  store ptr %t15, ptr %a16
  %t17 = load ptr, ptr %a12
  %t18 = ptrtoint ptr %t17 to i64
  %t19 = call i64 asm sideeffect "svc #0", "={x0},0,{x1},{x2},{x3},{x4},{x5},{x8},~{memory},~{cc}"(i64 0, i64 128, i64 %t18, i64 0, i64 0, i64 0, i64 123)
  store i64 %t19, ptr %a20
  store i64 0, ptr %a21
  store i64 0, ptr %a22
  br label %loop_cond23
loop_cond23:
  %t26 = load i64, ptr %a21
  %t27 = icmp slt i64 %t26, 128
  br i1 %t27, label %loop_body24, label %loop_exit25
loop_body24:
  %t28 = load i64, ptr %a21
  %t29 = add i64 %t28, 1
  %t30 = load i64, ptr %a22
  %t31 = load ptr, ptr %a12
  %t32 = load i64, ptr %a21
  %t33 = getelementptr i8, ptr %t31, i64 %t32
  %t34 = load i8, ptr %t33, align 1
  %t35 = zext i8 %t34 to i64
  store i64 %t35, ptr %a36
  store i64 0, ptr %a37
  br label %loop_cond38
loop_cond38:
  %t41 = load i64, ptr %a36
  %t42 = icmp sgt i64 %t41, 0
  br i1 %t42, label %loop_body39, label %loop_exit40
loop_body39:
  %t43 = load i64, ptr %a36
  %t44 = sdiv i64 %t43, 2
  %t45 = load i64, ptr %a37
  %t46 = load i64, ptr %a36
  %t47 = srem i64 %t46, 2
  %t48 = add i64 %t45, %t47
  store i64 %t44, ptr %a36
  store i64 %t48, ptr %a37
  br label %loop_cond38
loop_exit40:
  %t49 = load i64, ptr %a37
  %t50 = add i64 %t30, %t49
  store i64 %t29, ptr %a21
  store i64 %t50, ptr %a22
  br label %loop_cond23
loop_exit25:
  %t51 = load i64, ptr %a22
  store i64 %t51, ptr %a52
  %t53 = load i64, ptr %a20
  %t54 = icmp slt i64 %t53, 0
  store i1 %t54, ptr %a55
  br i1 %t54, label %join57, label %rhs56
rhs56:
  %t58 = load i64, ptr %a52
  %t59 = icmp slt i64 %t58, 1
  store i1 %t59, ptr %a55
  br label %join57
join57:
  %t60 = load i1, ptr %a55
  br i1 %t60, label %then62, label %else63
then62:
  store i64 1, ptr %a61
  br label %join64
else63:
  %t65 = load i64, ptr %a52
  store i64 %t65, ptr %a61
  br label %join64
join64:
  %t66 = load i64, ptr %a61
  store i64 %t66, ptr %a67
  %t68 = load i64, ptr %a67
  %t69 = getelementptr i8, ptr @ax_runtime_state, i64 16
  store i64 %t68, ptr %t69, align 1
  store i8 0, ptr %a70
  %t71 = load i64, ptr %a67
  store i64 %t71, ptr %a6
  br label %join9
join9:
  %t72 = load i64, ptr %a6
  ret i64 %t72
}

; rt_again  graph:9163015d66ea28e2
define internal i64 @ax_rt_again__par() "no-builtins" {
entry:
  ret i64 11
}

; rt_again  graph:9163015d66ea28e2
define internal i64 @ax_rt_again__seq() "no-builtins" {
entry:
  ret i64 11
}

; rt_nonblock_flag  graph:5e443fd254ad9825
define internal i64 @ax_rt_nonblock_flag__par() "no-builtins" {
entry:
  ret i64 2048
}

; rt_nonblock_flag  graph:5e443fd254ad9825
define internal i64 @ax_rt_nonblock_flag__seq() "no-builtins" {
entry:
  ret i64 2048
}

; rt_socket_level  graph:9f8c5953245c82df
define internal i64 @ax_rt_socket_level__par() "no-builtins" {
entry:
  ret i64 1
}

; rt_socket_level  graph:9f8c5953245c82df
define internal i64 @ax_rt_socket_level__seq() "no-builtins" {
entry:
  ret i64 1
}

; rt_reuseaddr  graph:8172014d9cae1709
define internal i64 @ax_rt_reuseaddr__par() "no-builtins" {
entry:
  ret i64 2
}

; rt_reuseaddr  graph:8172014d9cae1709
define internal i64 @ax_rt_reuseaddr__seq() "no-builtins" {
entry:
  ret i64 2
}

; rt_address  graph:82c718e10d48b51b
define internal void @ax_rt_address__seq(ptr %p_p) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a5 = alloca i8
  store ptr %p_p, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = trunc i64 2 to i8
  %t4 = getelementptr i8, ptr %t2, i64 0
  store i8 %t3, ptr %t4, align 1
  store i8 0, ptr %a5
  %t6 = load ptr, ptr %a1
  %t7 = trunc i64 0 to i8
  %t8 = getelementptr i8, ptr %t6, i64 1
  store i8 %t7, ptr %t8, align 1
  ret void
}

; rt_lower  graph:221a167c60faa7b3
define internal i8 @ax_rt_lower__par(i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca i8
  %a4 = alloca i1
  %a10 = alloca i8
  store i8 %p_c, ptr %a1
  %t2 = load i8, ptr %a1
  %t3 = icmp uge i8 %t2, 65
  store i1 %t3, ptr %a4
  br i1 %t3, label %rhs5, label %join6
rhs5:
  %t7 = load i8, ptr %a1
  %t8 = icmp ule i8 %t7, 90
  store i1 %t8, ptr %a4
  br label %join6
join6:
  %t9 = load i1, ptr %a4
  br i1 %t9, label %then11, label %else12
then11:
  %t14 = load i8, ptr %a1
  %t15 = zext i8 %t14 to i64
  %t16 = add i64 %t15, 32
  %t17 = trunc i64 %t16 to i8
  store i8 %t17, ptr %a10
  br label %join13
else12:
  %t18 = load i8, ptr %a1
  store i8 %t18, ptr %a10
  br label %join13
join13:
  %t19 = load i8, ptr %a10
  ret i8 %t19
}

; rt_lower  graph:221a167c60faa7b3
define internal i8 @ax_rt_lower__seq(i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca i8
  %a4 = alloca i1
  %a10 = alloca i8
  store i8 %p_c, ptr %a1
  %t2 = load i8, ptr %a1
  %t3 = icmp uge i8 %t2, 65
  store i1 %t3, ptr %a4
  br i1 %t3, label %rhs5, label %join6
rhs5:
  %t7 = load i8, ptr %a1
  %t8 = icmp ule i8 %t7, 90
  store i1 %t8, ptr %a4
  br label %join6
join6:
  %t9 = load i1, ptr %a4
  br i1 %t9, label %then11, label %else12
then11:
  %t14 = load i8, ptr %a1
  %t15 = zext i8 %t14 to i64
  %t16 = add i64 %t15, 32
  %t17 = trunc i64 %t16 to i8
  store i8 %t17, ptr %a10
  br label %join13
else12:
  %t18 = load i8, ptr %a1
  store i8 %t18, ptr %a10
  br label %join13
join13:
  %t19 = load i8, ptr %a10
  ret i8 %t19
}

; rt_match  graph:ebd11855a7e20706
define internal i1 @ax_rt_match__par(%ax_arr %p_a, i64 %p_at, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a19 = alloca i1
  %a22 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_at, ptr %a4
  store %ax_arr %p_b, ptr %a5
  %t7 = extractvalue %ax_arr %p_b, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a4
  %t15 = load i64, ptr %a13
  %t16 = add i64 %t14, %t15
  %t17 = load i64, ptr %a10
  %t18 = icmp sle i64 %t16, %t17
  store i1 %t18, ptr %a19
  br i1 %t18, label %rhs20, label %join21
rhs20:
  store i64 0, ptr %a22
  store i1 true, ptr %a23
  br label %loop_cond24
loop_cond24:
  %t27 = load i1, ptr %a23
  store i1 %t27, ptr %a28
  br i1 %t27, label %rhs29, label %join30
rhs29:
  %t31 = load i64, ptr %a22
  %t32 = load i64, ptr %a13
  %t33 = icmp slt i64 %t31, %t32
  store i1 %t33, ptr %a28
  br label %join30
join30:
  %t34 = load i1, ptr %a28
  br i1 %t34, label %loop_body25, label %loop_exit26
loop_body25:
  %t35 = load i64, ptr %a22
  %t36 = add i64 %t35, 1
  %t37 = load %ax_arr, ptr %a1
  %t38 = load i64, ptr %a4
  %t39 = load i64, ptr %a22
  %t40 = add i64 %t38, %t39
  %t41 = extractvalue %ax_arr %t37, 0
  %t42 = extractvalue %ax_arr %t37, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = load %ax_arr, ptr %a5
  %t46 = load i64, ptr %a22
  %t47 = extractvalue %ax_arr %t45, 0
  %t48 = extractvalue %ax_arr %t45, 1
  %t49 = getelementptr inbounds i8, ptr %t47, i64 %t46
  %t50 = load i8, ptr %t49
  %t51 = icmp eq i8 %t44, %t50
  store i64 %t36, ptr %a22
  store i1 %t51, ptr %a23
  br label %loop_cond24
loop_exit26:
  %t52 = load i1, ptr %a23
  store i1 %t52, ptr %a19
  br label %join21
join21:
  %t53 = load i1, ptr %a19
  %t54 = load i64, ptr %a2
  %t55 = icmp ne i64 %t54, 0
  %t56 = load %ax_arr, ptr %a1
  br i1 %t55, label %free57, label %cont58
free57:
  %t59 = extractvalue %ax_arr %t56, 0
  %t60 = extractvalue %ax_arr %t56, 1
  %t61 = mul i64 %t60, 1
  call void @ax_free(ptr %t59, i64 %t61)
  br label %cont58
cont58:
  %t62 = load i64, ptr %a6
  %t63 = icmp ne i64 %t62, 0
  %t64 = load %ax_arr, ptr %a5
  br i1 %t63, label %free65, label %cont66
free65:
  %t67 = extractvalue %ax_arr %t64, 0
  %t68 = extractvalue %ax_arr %t64, 1
  %t69 = mul i64 %t68, 1
  call void @ax_free(ptr %t67, i64 %t69)
  br label %cont66
cont66:
  ret i1 %t53
}

; rt_match  graph:ebd11855a7e20706
define internal i1 @ax_rt_match__seq(%ax_arr %p_a, i64 %p_at, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a19 = alloca i1
  %a22 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_at, ptr %a4
  store %ax_arr %p_b, ptr %a5
  %t7 = extractvalue %ax_arr %p_b, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a4
  %t15 = load i64, ptr %a13
  %t16 = add i64 %t14, %t15
  %t17 = load i64, ptr %a10
  %t18 = icmp sle i64 %t16, %t17
  store i1 %t18, ptr %a19
  br i1 %t18, label %rhs20, label %join21
rhs20:
  store i64 0, ptr %a22
  store i1 true, ptr %a23
  br label %loop_cond24
loop_cond24:
  %t27 = load i1, ptr %a23
  store i1 %t27, ptr %a28
  br i1 %t27, label %rhs29, label %join30
rhs29:
  %t31 = load i64, ptr %a22
  %t32 = load i64, ptr %a13
  %t33 = icmp slt i64 %t31, %t32
  store i1 %t33, ptr %a28
  br label %join30
join30:
  %t34 = load i1, ptr %a28
  br i1 %t34, label %loop_body25, label %loop_exit26
loop_body25:
  %t35 = load i64, ptr %a22
  %t36 = add i64 %t35, 1
  %t37 = load %ax_arr, ptr %a1
  %t38 = load i64, ptr %a4
  %t39 = load i64, ptr %a22
  %t40 = add i64 %t38, %t39
  %t41 = extractvalue %ax_arr %t37, 0
  %t42 = extractvalue %ax_arr %t37, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = load %ax_arr, ptr %a5
  %t46 = load i64, ptr %a22
  %t47 = extractvalue %ax_arr %t45, 0
  %t48 = extractvalue %ax_arr %t45, 1
  %t49 = getelementptr inbounds i8, ptr %t47, i64 %t46
  %t50 = load i8, ptr %t49
  %t51 = icmp eq i8 %t44, %t50
  store i64 %t36, ptr %a22
  store i1 %t51, ptr %a23
  br label %loop_cond24
loop_exit26:
  %t52 = load i1, ptr %a23
  store i1 %t52, ptr %a19
  br label %join21
join21:
  %t53 = load i1, ptr %a19
  %t54 = load i64, ptr %a2
  %t55 = icmp ne i64 %t54, 0
  %t56 = load %ax_arr, ptr %a1
  br i1 %t55, label %free57, label %cont58
free57:
  %t59 = extractvalue %ax_arr %t56, 0
  %t60 = extractvalue %ax_arr %t56, 1
  %t61 = mul i64 %t60, 1
  call void @ax_free(ptr %t59, i64 %t61)
  br label %cont58
cont58:
  %t62 = load i64, ptr %a6
  %t63 = icmp ne i64 %t62, 0
  %t64 = load %ax_arr, ptr %a5
  br i1 %t63, label %free65, label %cont66
free65:
  %t67 = extractvalue %ax_arr %t64, 0
  %t68 = extractvalue %ax_arr %t64, 1
  %t69 = mul i64 %t68, 1
  call void @ax_free(ptr %t67, i64 %t69)
  br label %cont66
cont66:
  ret i1 %t53
}

; rt_match_ci  graph:9e1e707f1e085e6d
define internal i1 @ax_rt_match_ci__par(%ax_arr %p_a, i64 %p_at, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a19 = alloca i1
  %a22 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_at, ptr %a4
  store %ax_arr %p_b, ptr %a5
  %t7 = extractvalue %ax_arr %p_b, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a4
  %t15 = load i64, ptr %a13
  %t16 = add i64 %t14, %t15
  %t17 = load i64, ptr %a10
  %t18 = icmp sle i64 %t16, %t17
  store i1 %t18, ptr %a19
  br i1 %t18, label %rhs20, label %join21
rhs20:
  store i64 0, ptr %a22
  store i1 true, ptr %a23
  br label %loop_cond24
loop_cond24:
  %t27 = load i1, ptr %a23
  store i1 %t27, ptr %a28
  br i1 %t27, label %rhs29, label %join30
rhs29:
  %t31 = load i64, ptr %a22
  %t32 = load i64, ptr %a13
  %t33 = icmp slt i64 %t31, %t32
  store i1 %t33, ptr %a28
  br label %join30
join30:
  %t34 = load i1, ptr %a28
  br i1 %t34, label %loop_body25, label %loop_exit26
loop_body25:
  %t35 = load i64, ptr %a22
  %t36 = add i64 %t35, 1
  %t37 = load %ax_arr, ptr %a1
  %t38 = load i64, ptr %a4
  %t39 = load i64, ptr %a22
  %t40 = add i64 %t38, %t39
  %t41 = extractvalue %ax_arr %t37, 0
  %t42 = extractvalue %ax_arr %t37, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = call i8 @ax_rt_lower__par(i8 %t44)
  %t46 = load %ax_arr, ptr %a5
  %t47 = load i64, ptr %a22
  %t48 = extractvalue %ax_arr %t46, 0
  %t49 = extractvalue %ax_arr %t46, 1
  %t50 = getelementptr inbounds i8, ptr %t48, i64 %t47
  %t51 = load i8, ptr %t50
  %t52 = call i8 @ax_rt_lower__par(i8 %t51)
  %t53 = icmp eq i8 %t45, %t52
  store i64 %t36, ptr %a22
  store i1 %t53, ptr %a23
  br label %loop_cond24
loop_exit26:
  %t54 = load i1, ptr %a23
  store i1 %t54, ptr %a19
  br label %join21
join21:
  %t55 = load i1, ptr %a19
  %t56 = load i64, ptr %a2
  %t57 = icmp ne i64 %t56, 0
  %t58 = load %ax_arr, ptr %a1
  br i1 %t57, label %free59, label %cont60
free59:
  %t61 = extractvalue %ax_arr %t58, 0
  %t62 = extractvalue %ax_arr %t58, 1
  %t63 = mul i64 %t62, 1
  call void @ax_free(ptr %t61, i64 %t63)
  br label %cont60
cont60:
  %t64 = load i64, ptr %a6
  %t65 = icmp ne i64 %t64, 0
  %t66 = load %ax_arr, ptr %a5
  br i1 %t65, label %free67, label %cont68
free67:
  %t69 = extractvalue %ax_arr %t66, 0
  %t70 = extractvalue %ax_arr %t66, 1
  %t71 = mul i64 %t70, 1
  call void @ax_free(ptr %t69, i64 %t71)
  br label %cont68
cont68:
  ret i1 %t55
}

; rt_match_ci  graph:9e1e707f1e085e6d
define internal i1 @ax_rt_match_ci__seq(%ax_arr %p_a, i64 %p_at, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a19 = alloca i1
  %a22 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_at, ptr %a4
  store %ax_arr %p_b, ptr %a5
  %t7 = extractvalue %ax_arr %p_b, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a4
  %t15 = load i64, ptr %a13
  %t16 = add i64 %t14, %t15
  %t17 = load i64, ptr %a10
  %t18 = icmp sle i64 %t16, %t17
  store i1 %t18, ptr %a19
  br i1 %t18, label %rhs20, label %join21
rhs20:
  store i64 0, ptr %a22
  store i1 true, ptr %a23
  br label %loop_cond24
loop_cond24:
  %t27 = load i1, ptr %a23
  store i1 %t27, ptr %a28
  br i1 %t27, label %rhs29, label %join30
rhs29:
  %t31 = load i64, ptr %a22
  %t32 = load i64, ptr %a13
  %t33 = icmp slt i64 %t31, %t32
  store i1 %t33, ptr %a28
  br label %join30
join30:
  %t34 = load i1, ptr %a28
  br i1 %t34, label %loop_body25, label %loop_exit26
loop_body25:
  %t35 = load i64, ptr %a22
  %t36 = add i64 %t35, 1
  %t37 = load %ax_arr, ptr %a1
  %t38 = load i64, ptr %a4
  %t39 = load i64, ptr %a22
  %t40 = add i64 %t38, %t39
  %t41 = extractvalue %ax_arr %t37, 0
  %t42 = extractvalue %ax_arr %t37, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = call i8 @ax_rt_lower__seq(i8 %t44)
  %t46 = load %ax_arr, ptr %a5
  %t47 = load i64, ptr %a22
  %t48 = extractvalue %ax_arr %t46, 0
  %t49 = extractvalue %ax_arr %t46, 1
  %t50 = getelementptr inbounds i8, ptr %t48, i64 %t47
  %t51 = load i8, ptr %t50
  %t52 = call i8 @ax_rt_lower__seq(i8 %t51)
  %t53 = icmp eq i8 %t45, %t52
  store i64 %t36, ptr %a22
  store i1 %t53, ptr %a23
  br label %loop_cond24
loop_exit26:
  %t54 = load i1, ptr %a23
  store i1 %t54, ptr %a19
  br label %join21
join21:
  %t55 = load i1, ptr %a19
  %t56 = load i64, ptr %a2
  %t57 = icmp ne i64 %t56, 0
  %t58 = load %ax_arr, ptr %a1
  br i1 %t57, label %free59, label %cont60
free59:
  %t61 = extractvalue %ax_arr %t58, 0
  %t62 = extractvalue %ax_arr %t58, 1
  %t63 = mul i64 %t62, 1
  call void @ax_free(ptr %t61, i64 %t63)
  br label %cont60
cont60:
  %t64 = load i64, ptr %a6
  %t65 = icmp ne i64 %t64, 0
  %t66 = load %ax_arr, ptr %a5
  br i1 %t65, label %free67, label %cont68
free67:
  %t69 = extractvalue %ax_arr %t66, 0
  %t70 = extractvalue %ax_arr %t66, 1
  %t71 = mul i64 %t70, 1
  call void @ax_free(ptr %t69, i64 %t71)
  br label %cont68
cont68:
  ret i1 %t55
}

; rt_find  graph:eb5f2734a877d473
define internal i64 @ax_rt_find__par(%ax_arr %p_a, %ax_arr %p_b, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a7 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a15 = alloca i64
  %a16 = alloca i64
  %a22 = alloca i1
  %a39 = alloca i64
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_b, ptr %a4
  %t6 = extractvalue %ax_arr %p_b, 2
  store i64 %t6, ptr %a5
  store i64 %p_start, ptr %a7
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a4
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a7
  store i64 %t14, ptr %a15
  store i64 -1, ptr %a16
  br label %loop_cond17
loop_cond17:
  %t20 = load i64, ptr %a16
  %t21 = icmp slt i64 %t20, 0
  store i1 %t21, ptr %a22
  br i1 %t21, label %rhs23, label %join24
rhs23:
  %t25 = load i64, ptr %a15
  %t26 = load i64, ptr %a13
  %t27 = add i64 %t25, %t26
  %t28 = load i64, ptr %a10
  %t29 = icmp sle i64 %t27, %t28
  store i1 %t29, ptr %a22
  br label %join24
join24:
  %t30 = load i1, ptr %a22
  br i1 %t30, label %loop_body18, label %loop_exit19
loop_body18:
  %t31 = load i64, ptr %a15
  %t32 = add i64 %t31, 1
  %t33 = load %ax_arr, ptr %a1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = load i64, ptr %a15
  %t36 = load %ax_arr, ptr %a4
  %t37 = insertvalue %ax_arr %t36, i64 0, 2
  %t38 = call i1 @ax_rt_match__par(%ax_arr %t34, i64 %t35, %ax_arr %t37)
  br i1 %t38, label %then40, label %else41
then40:
  %t43 = load i64, ptr %a15
  store i64 %t43, ptr %a39
  br label %join42
else41:
  store i64 -1, ptr %a39
  br label %join42
join42:
  %t44 = load i64, ptr %a39
  store i64 %t32, ptr %a15
  store i64 %t44, ptr %a16
  br label %loop_cond17
loop_exit19:
  %t45 = load i64, ptr %a16
  %t46 = load i64, ptr %a2
  %t47 = icmp ne i64 %t46, 0
  %t48 = load %ax_arr, ptr %a1
  br i1 %t47, label %free49, label %cont50
free49:
  %t51 = extractvalue %ax_arr %t48, 0
  %t52 = extractvalue %ax_arr %t48, 1
  %t53 = mul i64 %t52, 1
  call void @ax_free(ptr %t51, i64 %t53)
  br label %cont50
cont50:
  %t54 = load i64, ptr %a5
  %t55 = icmp ne i64 %t54, 0
  %t56 = load %ax_arr, ptr %a4
  br i1 %t55, label %free57, label %cont58
free57:
  %t59 = extractvalue %ax_arr %t56, 0
  %t60 = extractvalue %ax_arr %t56, 1
  %t61 = mul i64 %t60, 1
  call void @ax_free(ptr %t59, i64 %t61)
  br label %cont58
cont58:
  ret i64 %t45
}

; rt_find  graph:eb5f2734a877d473
define internal i64 @ax_rt_find__seq(%ax_arr %p_a, %ax_arr %p_b, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a7 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a15 = alloca i64
  %a16 = alloca i64
  %a22 = alloca i1
  %a39 = alloca i64
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_b, ptr %a4
  %t6 = extractvalue %ax_arr %p_b, 2
  store i64 %t6, ptr %a5
  store i64 %p_start, ptr %a7
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a4
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a7
  store i64 %t14, ptr %a15
  store i64 -1, ptr %a16
  br label %loop_cond17
loop_cond17:
  %t20 = load i64, ptr %a16
  %t21 = icmp slt i64 %t20, 0
  store i1 %t21, ptr %a22
  br i1 %t21, label %rhs23, label %join24
rhs23:
  %t25 = load i64, ptr %a15
  %t26 = load i64, ptr %a13
  %t27 = add i64 %t25, %t26
  %t28 = load i64, ptr %a10
  %t29 = icmp sle i64 %t27, %t28
  store i1 %t29, ptr %a22
  br label %join24
join24:
  %t30 = load i1, ptr %a22
  br i1 %t30, label %loop_body18, label %loop_exit19
loop_body18:
  %t31 = load i64, ptr %a15
  %t32 = add i64 %t31, 1
  %t33 = load %ax_arr, ptr %a1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = load i64, ptr %a15
  %t36 = load %ax_arr, ptr %a4
  %t37 = insertvalue %ax_arr %t36, i64 0, 2
  %t38 = call i1 @ax_rt_match__seq(%ax_arr %t34, i64 %t35, %ax_arr %t37)
  br i1 %t38, label %then40, label %else41
then40:
  %t43 = load i64, ptr %a15
  store i64 %t43, ptr %a39
  br label %join42
else41:
  store i64 -1, ptr %a39
  br label %join42
join42:
  %t44 = load i64, ptr %a39
  store i64 %t32, ptr %a15
  store i64 %t44, ptr %a16
  br label %loop_cond17
loop_exit19:
  %t45 = load i64, ptr %a16
  %t46 = load i64, ptr %a2
  %t47 = icmp ne i64 %t46, 0
  %t48 = load %ax_arr, ptr %a1
  br i1 %t47, label %free49, label %cont50
free49:
  %t51 = extractvalue %ax_arr %t48, 0
  %t52 = extractvalue %ax_arr %t48, 1
  %t53 = mul i64 %t52, 1
  call void @ax_free(ptr %t51, i64 %t53)
  br label %cont50
cont50:
  %t54 = load i64, ptr %a5
  %t55 = icmp ne i64 %t54, 0
  %t56 = load %ax_arr, ptr %a4
  br i1 %t55, label %free57, label %cont58
free57:
  %t59 = extractvalue %ax_arr %t56, 0
  %t60 = extractvalue %ax_arr %t56, 1
  %t61 = mul i64 %t60, 1
  call void @ax_free(ptr %t59, i64 %t61)
  br label %cont58
cont58:
  ret i64 %t45
}

; rt_header  graph:6e58388c67459167
define internal i64 @ax_rt_header__par(%ax_arr %p_a, %ax_arr %p_key, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a7 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a15 = alloca i64
  %a16 = alloca i64
  %a22 = alloca i1
  %a35 = alloca i1
  %a47 = alloca i1
  %a57 = alloca i64
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_key, ptr %a4
  %t6 = extractvalue %ax_arr %p_key, 2
  store i64 %t6, ptr %a5
  store i64 %p_start, ptr %a7
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a4
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a7
  store i64 %t14, ptr %a15
  store i64 -1, ptr %a16
  br label %loop_cond17
loop_cond17:
  %t20 = load i64, ptr %a16
  %t21 = icmp slt i64 %t20, 0
  store i1 %t21, ptr %a22
  br i1 %t21, label %rhs23, label %join24
rhs23:
  %t25 = load i64, ptr %a15
  %t26 = load i64, ptr %a13
  %t27 = add i64 %t25, %t26
  %t28 = load i64, ptr %a10
  %t29 = icmp sle i64 %t27, %t28
  store i1 %t29, ptr %a22
  br label %join24
join24:
  %t30 = load i1, ptr %a22
  br i1 %t30, label %loop_body18, label %loop_exit19
loop_body18:
  %t31 = load i64, ptr %a15
  %t32 = add i64 %t31, 1
  %t33 = load i64, ptr %a15
  %t34 = icmp eq i64 %t33, 0
  store i1 %t34, ptr %a35
  br i1 %t34, label %join37, label %rhs36
rhs36:
  %t38 = load %ax_arr, ptr %a1
  %t39 = load i64, ptr %a15
  %t40 = sub i64 %t39, 1
  %t41 = extractvalue %ax_arr %t38, 0
  %t42 = extractvalue %ax_arr %t38, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = icmp eq i8 %t44, 10
  store i1 %t45, ptr %a35
  br label %join37
join37:
  %t46 = load i1, ptr %a35
  store i1 %t46, ptr %a47
  br i1 %t46, label %rhs48, label %join49
rhs48:
  %t50 = load %ax_arr, ptr %a1
  %t51 = insertvalue %ax_arr %t50, i64 0, 2
  %t52 = load i64, ptr %a15
  %t53 = load %ax_arr, ptr %a4
  %t54 = insertvalue %ax_arr %t53, i64 0, 2
  %t55 = call i1 @ax_rt_match_ci__par(%ax_arr %t51, i64 %t52, %ax_arr %t54)
  store i1 %t55, ptr %a47
  br label %join49
join49:
  %t56 = load i1, ptr %a47
  br i1 %t56, label %then58, label %else59
then58:
  %t61 = load i64, ptr %a15
  %t62 = load i64, ptr %a13
  %t63 = add i64 %t61, %t62
  store i64 %t63, ptr %a57
  br label %join60
else59:
  store i64 -1, ptr %a57
  br label %join60
join60:
  %t64 = load i64, ptr %a57
  store i64 %t32, ptr %a15
  store i64 %t64, ptr %a16
  br label %loop_cond17
loop_exit19:
  %t65 = load i64, ptr %a16
  %t66 = load i64, ptr %a2
  %t67 = icmp ne i64 %t66, 0
  %t68 = load %ax_arr, ptr %a1
  br i1 %t67, label %free69, label %cont70
free69:
  %t71 = extractvalue %ax_arr %t68, 0
  %t72 = extractvalue %ax_arr %t68, 1
  %t73 = mul i64 %t72, 1
  call void @ax_free(ptr %t71, i64 %t73)
  br label %cont70
cont70:
  %t74 = load i64, ptr %a5
  %t75 = icmp ne i64 %t74, 0
  %t76 = load %ax_arr, ptr %a4
  br i1 %t75, label %free77, label %cont78
free77:
  %t79 = extractvalue %ax_arr %t76, 0
  %t80 = extractvalue %ax_arr %t76, 1
  %t81 = mul i64 %t80, 1
  call void @ax_free(ptr %t79, i64 %t81)
  br label %cont78
cont78:
  ret i64 %t65
}

; rt_header  graph:6e58388c67459167
define internal i64 @ax_rt_header__seq(%ax_arr %p_a, %ax_arr %p_key, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a7 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a15 = alloca i64
  %a16 = alloca i64
  %a22 = alloca i1
  %a35 = alloca i1
  %a47 = alloca i1
  %a57 = alloca i64
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_key, ptr %a4
  %t6 = extractvalue %ax_arr %p_key, 2
  store i64 %t6, ptr %a5
  store i64 %p_start, ptr %a7
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a4
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load i64, ptr %a7
  store i64 %t14, ptr %a15
  store i64 -1, ptr %a16
  br label %loop_cond17
loop_cond17:
  %t20 = load i64, ptr %a16
  %t21 = icmp slt i64 %t20, 0
  store i1 %t21, ptr %a22
  br i1 %t21, label %rhs23, label %join24
rhs23:
  %t25 = load i64, ptr %a15
  %t26 = load i64, ptr %a13
  %t27 = add i64 %t25, %t26
  %t28 = load i64, ptr %a10
  %t29 = icmp sle i64 %t27, %t28
  store i1 %t29, ptr %a22
  br label %join24
join24:
  %t30 = load i1, ptr %a22
  br i1 %t30, label %loop_body18, label %loop_exit19
loop_body18:
  %t31 = load i64, ptr %a15
  %t32 = add i64 %t31, 1
  %t33 = load i64, ptr %a15
  %t34 = icmp eq i64 %t33, 0
  store i1 %t34, ptr %a35
  br i1 %t34, label %join37, label %rhs36
rhs36:
  %t38 = load %ax_arr, ptr %a1
  %t39 = load i64, ptr %a15
  %t40 = sub i64 %t39, 1
  %t41 = extractvalue %ax_arr %t38, 0
  %t42 = extractvalue %ax_arr %t38, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  %t44 = load i8, ptr %t43
  %t45 = icmp eq i8 %t44, 10
  store i1 %t45, ptr %a35
  br label %join37
join37:
  %t46 = load i1, ptr %a35
  store i1 %t46, ptr %a47
  br i1 %t46, label %rhs48, label %join49
rhs48:
  %t50 = load %ax_arr, ptr %a1
  %t51 = insertvalue %ax_arr %t50, i64 0, 2
  %t52 = load i64, ptr %a15
  %t53 = load %ax_arr, ptr %a4
  %t54 = insertvalue %ax_arr %t53, i64 0, 2
  %t55 = call i1 @ax_rt_match_ci__seq(%ax_arr %t51, i64 %t52, %ax_arr %t54)
  store i1 %t55, ptr %a47
  br label %join49
join49:
  %t56 = load i1, ptr %a47
  br i1 %t56, label %then58, label %else59
then58:
  %t61 = load i64, ptr %a15
  %t62 = load i64, ptr %a13
  %t63 = add i64 %t61, %t62
  store i64 %t63, ptr %a57
  br label %join60
else59:
  store i64 -1, ptr %a57
  br label %join60
join60:
  %t64 = load i64, ptr %a57
  store i64 %t32, ptr %a15
  store i64 %t64, ptr %a16
  br label %loop_cond17
loop_exit19:
  %t65 = load i64, ptr %a16
  %t66 = load i64, ptr %a2
  %t67 = icmp ne i64 %t66, 0
  %t68 = load %ax_arr, ptr %a1
  br i1 %t67, label %free69, label %cont70
free69:
  %t71 = extractvalue %ax_arr %t68, 0
  %t72 = extractvalue %ax_arr %t68, 1
  %t73 = mul i64 %t72, 1
  call void @ax_free(ptr %t71, i64 %t73)
  br label %cont70
cont70:
  %t74 = load i64, ptr %a5
  %t75 = icmp ne i64 %t74, 0
  %t76 = load %ax_arr, ptr %a4
  br i1 %t75, label %free77, label %cont78
free77:
  %t79 = extractvalue %ax_arr %t76, 0
  %t80 = extractvalue %ax_arr %t76, 1
  %t81 = mul i64 %t80, 1
  call void @ax_free(ptr %t79, i64 %t81)
  br label %cont78
cont78:
  ret i64 %t65
}

; rt_skip_space  graph:d3219cdc3a527cf2
define internal i64 @ax_rt_skip_space__par(%ax_arr %p_a, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a7 = alloca i64
  %a9 = alloca i64
  %a16 = alloca i1
  %a26 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_start, ptr %a4
  %t5 = load %ax_arr, ptr %a1
  %t6 = extractvalue %ax_arr %t5, 1
  store i64 %t6, ptr %a7
  %t8 = load i64, ptr %a4
  store i64 %t8, ptr %a9
  br label %loop_cond10
loop_cond10:
  %t13 = load i64, ptr %a9
  %t14 = load i64, ptr %a7
  %t15 = icmp slt i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  %t19 = load %ax_arr, ptr %a1
  %t20 = load i64, ptr %a9
  %t21 = extractvalue %ax_arr %t19, 0
  %t22 = extractvalue %ax_arr %t19, 1
  %t23 = getelementptr inbounds i8, ptr %t21, i64 %t20
  %t24 = load i8, ptr %t23
  %t25 = icmp eq i8 %t24, 32
  store i1 %t25, ptr %a26
  br i1 %t25, label %join28, label %rhs27
rhs27:
  %t29 = load %ax_arr, ptr %a1
  %t30 = load i64, ptr %a9
  %t31 = extractvalue %ax_arr %t29, 0
  %t32 = extractvalue %ax_arr %t29, 1
  %t33 = getelementptr inbounds i8, ptr %t31, i64 %t30
  %t34 = load i8, ptr %t33
  %t35 = icmp eq i8 %t34, 9
  store i1 %t35, ptr %a26
  br label %join28
join28:
  %t36 = load i1, ptr %a26
  store i1 %t36, ptr %a16
  br label %join18
join18:
  %t37 = load i1, ptr %a16
  br i1 %t37, label %loop_body11, label %loop_exit12
loop_body11:
  %t38 = load i64, ptr %a9
  %t39 = add i64 %t38, 1
  store i64 %t39, ptr %a9
  br label %loop_cond10
loop_exit12:
  %t40 = load i64, ptr %a9
  %t41 = load i64, ptr %a2
  %t42 = icmp ne i64 %t41, 0
  %t43 = load %ax_arr, ptr %a1
  br i1 %t42, label %free44, label %cont45
free44:
  %t46 = extractvalue %ax_arr %t43, 0
  %t47 = extractvalue %ax_arr %t43, 1
  %t48 = mul i64 %t47, 1
  call void @ax_free(ptr %t46, i64 %t48)
  br label %cont45
cont45:
  ret i64 %t40
}

; rt_skip_space  graph:d3219cdc3a527cf2
define internal i64 @ax_rt_skip_space__seq(%ax_arr %p_a, i64 %p_start) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a7 = alloca i64
  %a9 = alloca i64
  %a16 = alloca i1
  %a26 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store i64 %p_start, ptr %a4
  %t5 = load %ax_arr, ptr %a1
  %t6 = extractvalue %ax_arr %t5, 1
  store i64 %t6, ptr %a7
  %t8 = load i64, ptr %a4
  store i64 %t8, ptr %a9
  br label %loop_cond10
loop_cond10:
  %t13 = load i64, ptr %a9
  %t14 = load i64, ptr %a7
  %t15 = icmp slt i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  %t19 = load %ax_arr, ptr %a1
  %t20 = load i64, ptr %a9
  %t21 = extractvalue %ax_arr %t19, 0
  %t22 = extractvalue %ax_arr %t19, 1
  %t23 = getelementptr inbounds i8, ptr %t21, i64 %t20
  %t24 = load i8, ptr %t23
  %t25 = icmp eq i8 %t24, 32
  store i1 %t25, ptr %a26
  br i1 %t25, label %join28, label %rhs27
rhs27:
  %t29 = load %ax_arr, ptr %a1
  %t30 = load i64, ptr %a9
  %t31 = extractvalue %ax_arr %t29, 0
  %t32 = extractvalue %ax_arr %t29, 1
  %t33 = getelementptr inbounds i8, ptr %t31, i64 %t30
  %t34 = load i8, ptr %t33
  %t35 = icmp eq i8 %t34, 9
  store i1 %t35, ptr %a26
  br label %join28
join28:
  %t36 = load i1, ptr %a26
  store i1 %t36, ptr %a16
  br label %join18
join18:
  %t37 = load i1, ptr %a16
  br i1 %t37, label %loop_body11, label %loop_exit12
loop_body11:
  %t38 = load i64, ptr %a9
  %t39 = add i64 %t38, 1
  store i64 %t39, ptr %a9
  br label %loop_cond10
loop_exit12:
  %t40 = load i64, ptr %a9
  %t41 = load i64, ptr %a2
  %t42 = icmp ne i64 %t41, 0
  %t43 = load %ax_arr, ptr %a1
  br i1 %t42, label %free44, label %cont45
free44:
  %t46 = extractvalue %ax_arr %t43, 0
  %t47 = extractvalue %ax_arr %t43, 1
  %t48 = mul i64 %t47, 1
  call void @ax_free(ptr %t46, i64 %t48)
  br label %cont45
cont45:
  ret i64 %t40
}

; rt_body_length  graph:b5a8bfdc1897e578
define internal i64 @ax_rt_body_length__par(%ax_arr %p_headers) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a14 = alloca i64
  %a23 = alloca i64
  %a29 = alloca i64
  %a42 = alloca i64
  %a50 = alloca i64
  %a52 = alloca i64
  %a53 = alloca i64
  %a54 = alloca i64
  %a61 = alloca i1
  %a72 = alloca i1
  %a83 = alloca i1
  %a106 = alloca i1
  %a112 = alloca i64
  %a120 = alloca i64
  %a125 = alloca i1
  %a136 = alloca i1
  %a148 = alloca i64
  %a155 = alloca i64
  store %ax_arr %p_headers, ptr %a1
  %t3 = extractvalue %ax_arr %p_headers, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load %ax_arr, ptr %a1
  %t8 = insertvalue %ax_arr %t7, i64 0, 2
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.20, 0
  %t10 = insertvalue %ax_arr %t9, i64 15, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = call i64 @ax_rt_header__par(%ax_arr %t8, %ax_arr %t12, i64 0)
  store i64 %t13, ptr %a14
  %t15 = load %ax_arr, ptr %a1
  %t16 = insertvalue %ax_arr %t15, i64 0, 2
  %t17 = insertvalue %ax_arr undef, ptr @.bytes.21, 0
  %t18 = insertvalue %ax_arr %t17, i64 18, 1
  %t19 = insertvalue %ax_arr %t18, i64 0, 2
  %t20 = insertvalue %ax_arr %t19, i64 0, 2
  %t21 = call i64 @ax_rt_header__par(%ax_arr %t16, %ax_arr %t20, i64 0)
  %t22 = icmp sge i64 %t21, 0
  br i1 %t22, label %then24, label %else25
then24:
  store i64 -1, ptr %a23
  br label %join26
else25:
  %t27 = load i64, ptr %a14
  %t28 = icmp slt i64 %t27, 0
  br i1 %t28, label %then30, label %else31
then30:
  store i64 0, ptr %a29
  br label %join32
else31:
  %t33 = load %ax_arr, ptr %a1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = insertvalue %ax_arr undef, ptr @.bytes.20, 0
  %t36 = insertvalue %ax_arr %t35, i64 15, 1
  %t37 = insertvalue %ax_arr %t36, i64 0, 2
  %t38 = insertvalue %ax_arr %t37, i64 0, 2
  %t39 = load i64, ptr %a14
  %t40 = call i64 @ax_rt_header__par(%ax_arr %t34, %ax_arr %t38, i64 %t39)
  %t41 = icmp sge i64 %t40, 0
  br i1 %t41, label %then43, label %else44
then43:
  store i64 -1, ptr %a42
  br label %join45
else44:
  %t46 = load %ax_arr, ptr %a1
  %t47 = insertvalue %ax_arr %t46, i64 0, 2
  %t48 = load i64, ptr %a14
  %t49 = call i64 @ax_rt_skip_space__par(%ax_arr %t47, i64 %t48)
  store i64 %t49, ptr %a50
  %t51 = load i64, ptr %a50
  store i64 %t51, ptr %a52
  store i64 0, ptr %a53
  store i64 0, ptr %a54
  br label %loop_cond55
loop_cond55:
  %t58 = load i64, ptr %a52
  %t59 = load i64, ptr %a6
  %t60 = icmp slt i64 %t58, %t59
  store i1 %t60, ptr %a61
  br i1 %t60, label %rhs62, label %join63
rhs62:
  %t64 = load %ax_arr, ptr %a1
  %t65 = load i64, ptr %a52
  %t66 = extractvalue %ax_arr %t64, 0
  %t67 = extractvalue %ax_arr %t64, 1
  %t68 = getelementptr inbounds i8, ptr %t66, i64 %t65
  %t69 = load i8, ptr %t68
  %t70 = icmp uge i8 %t69, 48
  store i1 %t70, ptr %a61
  br label %join63
join63:
  %t71 = load i1, ptr %a61
  store i1 %t71, ptr %a72
  br i1 %t71, label %rhs73, label %join74
rhs73:
  %t75 = load %ax_arr, ptr %a1
  %t76 = load i64, ptr %a52
  %t77 = extractvalue %ax_arr %t75, 0
  %t78 = extractvalue %ax_arr %t75, 1
  %t79 = getelementptr inbounds i8, ptr %t77, i64 %t76
  %t80 = load i8, ptr %t79
  %t81 = icmp ule i8 %t80, 57
  store i1 %t81, ptr %a72
  br label %join74
join74:
  %t82 = load i1, ptr %a72
  store i1 %t82, ptr %a83
  br i1 %t82, label %rhs84, label %join85
rhs84:
  %t86 = load i64, ptr %a53
  %t87 = icmp sle i64 %t86, 65536
  store i1 %t87, ptr %a83
  br label %join85
join85:
  %t88 = load i1, ptr %a83
  br i1 %t88, label %loop_body56, label %loop_exit57
loop_body56:
  %t89 = load i64, ptr %a52
  %t90 = add i64 %t89, 1
  %t91 = load i64, ptr %a53
  %t92 = mul i64 %t91, 10
  %t93 = load %ax_arr, ptr %a1
  %t94 = load i64, ptr %a52
  %t95 = extractvalue %ax_arr %t93, 0
  %t96 = extractvalue %ax_arr %t93, 1
  %t97 = getelementptr inbounds i8, ptr %t95, i64 %t94
  %t98 = load i8, ptr %t97
  %t99 = zext i8 %t98 to i64
  %t100 = add i64 %t92, %t99
  %t101 = sub i64 %t100, 48
  %t102 = load i64, ptr %a54
  %t103 = add i64 %t102, 1
  store i64 %t90, ptr %a52
  store i64 %t101, ptr %a53
  store i64 %t103, ptr %a54
  br label %loop_cond55
loop_exit57:
  %t104 = load i64, ptr %a54
  %t105 = icmp eq i64 %t104, 0
  store i1 %t105, ptr %a106
  br i1 %t105, label %join108, label %rhs107
rhs107:
  %t109 = load i64, ptr %a53
  %t110 = icmp sgt i64 %t109, 65536
  store i1 %t110, ptr %a106
  br label %join108
join108:
  %t111 = load i1, ptr %a106
  br i1 %t111, label %then113, label %else114
then113:
  store i64 -1, ptr %a112
  br label %join115
else114:
  %t116 = load %ax_arr, ptr %a1
  %t117 = insertvalue %ax_arr %t116, i64 0, 2
  %t118 = load i64, ptr %a52
  %t119 = call i64 @ax_rt_skip_space__par(%ax_arr %t117, i64 %t118)
  store i64 %t119, ptr %a120
  %t121 = load i64, ptr %a120
  %t122 = add i64 %t121, 1
  %t123 = load i64, ptr %a6
  %t124 = icmp slt i64 %t122, %t123
  store i1 %t124, ptr %a125
  br i1 %t124, label %rhs126, label %join127
rhs126:
  %t128 = load %ax_arr, ptr %a1
  %t129 = load i64, ptr %a120
  %t130 = extractvalue %ax_arr %t128, 0
  %t131 = extractvalue %ax_arr %t128, 1
  %t132 = getelementptr inbounds i8, ptr %t130, i64 %t129
  %t133 = load i8, ptr %t132
  %t134 = icmp eq i8 %t133, 13
  store i1 %t134, ptr %a125
  br label %join127
join127:
  %t135 = load i1, ptr %a125
  store i1 %t135, ptr %a136
  br i1 %t135, label %rhs137, label %join138
rhs137:
  %t139 = load %ax_arr, ptr %a1
  %t140 = load i64, ptr %a120
  %t141 = add i64 %t140, 1
  %t142 = extractvalue %ax_arr %t139, 0
  %t143 = extractvalue %ax_arr %t139, 1
  %t144 = getelementptr inbounds i8, ptr %t142, i64 %t141
  %t145 = load i8, ptr %t144
  %t146 = icmp eq i8 %t145, 10
  store i1 %t146, ptr %a136
  br label %join138
join138:
  %t147 = load i1, ptr %a136
  br i1 %t147, label %then149, label %else150
then149:
  %t152 = load i64, ptr %a53
  store i64 %t152, ptr %a148
  br label %join151
else150:
  store i64 -1, ptr %a148
  br label %join151
join151:
  %t153 = load i64, ptr %a148
  store i64 %t153, ptr %a112
  br label %join115
join115:
  %t154 = load i64, ptr %a112
  store i64 %t154, ptr %a155
  %t156 = load i64, ptr %a155
  store i64 %t156, ptr %a42
  br label %join45
join45:
  %t157 = load i64, ptr %a42
  store i64 %t157, ptr %a29
  br label %join32
join32:
  %t158 = load i64, ptr %a29
  store i64 %t158, ptr %a23
  br label %join26
join26:
  %t159 = load i64, ptr %a23
  %t160 = load i64, ptr %a2
  %t161 = icmp ne i64 %t160, 0
  %t162 = load %ax_arr, ptr %a1
  br i1 %t161, label %free163, label %cont164
free163:
  %t165 = extractvalue %ax_arr %t162, 0
  %t166 = extractvalue %ax_arr %t162, 1
  %t167 = mul i64 %t166, 1
  call void @ax_free(ptr %t165, i64 %t167)
  br label %cont164
cont164:
  ret i64 %t159
}

; rt_body_length  graph:b5a8bfdc1897e578
define internal i64 @ax_rt_body_length__seq(%ax_arr %p_headers) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a14 = alloca i64
  %a23 = alloca i64
  %a29 = alloca i64
  %a42 = alloca i64
  %a50 = alloca i64
  %a52 = alloca i64
  %a53 = alloca i64
  %a54 = alloca i64
  %a61 = alloca i1
  %a72 = alloca i1
  %a83 = alloca i1
  %a106 = alloca i1
  %a112 = alloca i64
  %a120 = alloca i64
  %a125 = alloca i1
  %a136 = alloca i1
  %a148 = alloca i64
  %a155 = alloca i64
  store %ax_arr %p_headers, ptr %a1
  %t3 = extractvalue %ax_arr %p_headers, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load %ax_arr, ptr %a1
  %t8 = insertvalue %ax_arr %t7, i64 0, 2
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.20, 0
  %t10 = insertvalue %ax_arr %t9, i64 15, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = call i64 @ax_rt_header__seq(%ax_arr %t8, %ax_arr %t12, i64 0)
  store i64 %t13, ptr %a14
  %t15 = load %ax_arr, ptr %a1
  %t16 = insertvalue %ax_arr %t15, i64 0, 2
  %t17 = insertvalue %ax_arr undef, ptr @.bytes.21, 0
  %t18 = insertvalue %ax_arr %t17, i64 18, 1
  %t19 = insertvalue %ax_arr %t18, i64 0, 2
  %t20 = insertvalue %ax_arr %t19, i64 0, 2
  %t21 = call i64 @ax_rt_header__seq(%ax_arr %t16, %ax_arr %t20, i64 0)
  %t22 = icmp sge i64 %t21, 0
  br i1 %t22, label %then24, label %else25
then24:
  store i64 -1, ptr %a23
  br label %join26
else25:
  %t27 = load i64, ptr %a14
  %t28 = icmp slt i64 %t27, 0
  br i1 %t28, label %then30, label %else31
then30:
  store i64 0, ptr %a29
  br label %join32
else31:
  %t33 = load %ax_arr, ptr %a1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = insertvalue %ax_arr undef, ptr @.bytes.20, 0
  %t36 = insertvalue %ax_arr %t35, i64 15, 1
  %t37 = insertvalue %ax_arr %t36, i64 0, 2
  %t38 = insertvalue %ax_arr %t37, i64 0, 2
  %t39 = load i64, ptr %a14
  %t40 = call i64 @ax_rt_header__seq(%ax_arr %t34, %ax_arr %t38, i64 %t39)
  %t41 = icmp sge i64 %t40, 0
  br i1 %t41, label %then43, label %else44
then43:
  store i64 -1, ptr %a42
  br label %join45
else44:
  %t46 = load %ax_arr, ptr %a1
  %t47 = insertvalue %ax_arr %t46, i64 0, 2
  %t48 = load i64, ptr %a14
  %t49 = call i64 @ax_rt_skip_space__seq(%ax_arr %t47, i64 %t48)
  store i64 %t49, ptr %a50
  %t51 = load i64, ptr %a50
  store i64 %t51, ptr %a52
  store i64 0, ptr %a53
  store i64 0, ptr %a54
  br label %loop_cond55
loop_cond55:
  %t58 = load i64, ptr %a52
  %t59 = load i64, ptr %a6
  %t60 = icmp slt i64 %t58, %t59
  store i1 %t60, ptr %a61
  br i1 %t60, label %rhs62, label %join63
rhs62:
  %t64 = load %ax_arr, ptr %a1
  %t65 = load i64, ptr %a52
  %t66 = extractvalue %ax_arr %t64, 0
  %t67 = extractvalue %ax_arr %t64, 1
  %t68 = getelementptr inbounds i8, ptr %t66, i64 %t65
  %t69 = load i8, ptr %t68
  %t70 = icmp uge i8 %t69, 48
  store i1 %t70, ptr %a61
  br label %join63
join63:
  %t71 = load i1, ptr %a61
  store i1 %t71, ptr %a72
  br i1 %t71, label %rhs73, label %join74
rhs73:
  %t75 = load %ax_arr, ptr %a1
  %t76 = load i64, ptr %a52
  %t77 = extractvalue %ax_arr %t75, 0
  %t78 = extractvalue %ax_arr %t75, 1
  %t79 = getelementptr inbounds i8, ptr %t77, i64 %t76
  %t80 = load i8, ptr %t79
  %t81 = icmp ule i8 %t80, 57
  store i1 %t81, ptr %a72
  br label %join74
join74:
  %t82 = load i1, ptr %a72
  store i1 %t82, ptr %a83
  br i1 %t82, label %rhs84, label %join85
rhs84:
  %t86 = load i64, ptr %a53
  %t87 = icmp sle i64 %t86, 65536
  store i1 %t87, ptr %a83
  br label %join85
join85:
  %t88 = load i1, ptr %a83
  br i1 %t88, label %loop_body56, label %loop_exit57
loop_body56:
  %t89 = load i64, ptr %a52
  %t90 = add i64 %t89, 1
  %t91 = load i64, ptr %a53
  %t92 = mul i64 %t91, 10
  %t93 = load %ax_arr, ptr %a1
  %t94 = load i64, ptr %a52
  %t95 = extractvalue %ax_arr %t93, 0
  %t96 = extractvalue %ax_arr %t93, 1
  %t97 = getelementptr inbounds i8, ptr %t95, i64 %t94
  %t98 = load i8, ptr %t97
  %t99 = zext i8 %t98 to i64
  %t100 = add i64 %t92, %t99
  %t101 = sub i64 %t100, 48
  %t102 = load i64, ptr %a54
  %t103 = add i64 %t102, 1
  store i64 %t90, ptr %a52
  store i64 %t101, ptr %a53
  store i64 %t103, ptr %a54
  br label %loop_cond55
loop_exit57:
  %t104 = load i64, ptr %a54
  %t105 = icmp eq i64 %t104, 0
  store i1 %t105, ptr %a106
  br i1 %t105, label %join108, label %rhs107
rhs107:
  %t109 = load i64, ptr %a53
  %t110 = icmp sgt i64 %t109, 65536
  store i1 %t110, ptr %a106
  br label %join108
join108:
  %t111 = load i1, ptr %a106
  br i1 %t111, label %then113, label %else114
then113:
  store i64 -1, ptr %a112
  br label %join115
else114:
  %t116 = load %ax_arr, ptr %a1
  %t117 = insertvalue %ax_arr %t116, i64 0, 2
  %t118 = load i64, ptr %a52
  %t119 = call i64 @ax_rt_skip_space__seq(%ax_arr %t117, i64 %t118)
  store i64 %t119, ptr %a120
  %t121 = load i64, ptr %a120
  %t122 = add i64 %t121, 1
  %t123 = load i64, ptr %a6
  %t124 = icmp slt i64 %t122, %t123
  store i1 %t124, ptr %a125
  br i1 %t124, label %rhs126, label %join127
rhs126:
  %t128 = load %ax_arr, ptr %a1
  %t129 = load i64, ptr %a120
  %t130 = extractvalue %ax_arr %t128, 0
  %t131 = extractvalue %ax_arr %t128, 1
  %t132 = getelementptr inbounds i8, ptr %t130, i64 %t129
  %t133 = load i8, ptr %t132
  %t134 = icmp eq i8 %t133, 13
  store i1 %t134, ptr %a125
  br label %join127
join127:
  %t135 = load i1, ptr %a125
  store i1 %t135, ptr %a136
  br i1 %t135, label %rhs137, label %join138
rhs137:
  %t139 = load %ax_arr, ptr %a1
  %t140 = load i64, ptr %a120
  %t141 = add i64 %t140, 1
  %t142 = extractvalue %ax_arr %t139, 0
  %t143 = extractvalue %ax_arr %t139, 1
  %t144 = getelementptr inbounds i8, ptr %t142, i64 %t141
  %t145 = load i8, ptr %t144
  %t146 = icmp eq i8 %t145, 10
  store i1 %t146, ptr %a136
  br label %join138
join138:
  %t147 = load i1, ptr %a136
  br i1 %t147, label %then149, label %else150
then149:
  %t152 = load i64, ptr %a53
  store i64 %t152, ptr %a148
  br label %join151
else150:
  store i64 -1, ptr %a148
  br label %join151
join151:
  %t153 = load i64, ptr %a148
  store i64 %t153, ptr %a112
  br label %join115
join115:
  %t154 = load i64, ptr %a112
  store i64 %t154, ptr %a155
  %t156 = load i64, ptr %a155
  store i64 %t156, ptr %a42
  br label %join45
join45:
  %t157 = load i64, ptr %a42
  store i64 %t157, ptr %a29
  br label %join32
join32:
  %t158 = load i64, ptr %a29
  store i64 %t158, ptr %a23
  br label %join26
join26:
  %t159 = load i64, ptr %a23
  %t160 = load i64, ptr %a2
  %t161 = icmp ne i64 %t160, 0
  %t162 = load %ax_arr, ptr %a1
  br i1 %t161, label %free163, label %cont164
free163:
  %t165 = extractvalue %ax_arr %t162, 0
  %t166 = extractvalue %ax_arr %t162, 1
  %t167 = mul i64 %t166, 1
  call void @ax_free(ptr %t165, i64 %t167)
  br label %cont164
cont164:
  ret i64 %t159
}

; rt_connection_token  graph:cc007414139e27c6
define internal i1 @ax_rt_connection_token__par(%ax_arr %p_headers, %ax_arr %p_token) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a20 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i64
  %a29 = alloca i1
  %a35 = alloca i1
  %a42 = alloca i1
  %a53 = alloca i1
  %a72 = alloca i1
  %a78 = alloca i1
  %a83 = alloca i1
  %a94 = alloca i1
  %a106 = alloca i1
  %a121 = alloca i1
  %a130 = alloca i1
  %a142 = alloca i1
  %a155 = alloca i1
  %a168 = alloca i1
  store %ax_arr %p_headers, ptr %a1
  %t3 = extractvalue %ax_arr %p_headers, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_token, ptr %a4
  %t6 = extractvalue %ax_arr %p_token, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load %ax_arr, ptr %a1
  %t14 = insertvalue %ax_arr %t13, i64 0, 2
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.22, 0
  %t16 = insertvalue %ax_arr %t15, i64 11, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = insertvalue %ax_arr %t17, i64 0, 2
  %t19 = call i64 @ax_rt_header__par(%ax_arr %t14, %ax_arr %t18, i64 0)
  store i64 %t19, ptr %a20
  %t21 = load i64, ptr %a20
  %t22 = icmp slt i64 %t21, 0
  br i1 %t22, label %then24, label %else25
then24:
  store i1 false, ptr %a23
  br label %join26
else25:
  %t27 = load i64, ptr %a20
  store i64 %t27, ptr %a28
  store i1 false, ptr %a29
  br label %loop_cond30
loop_cond30:
  %t33 = load i1, ptr %a29
  %t34 = xor i1 %t33, true
  store i1 %t34, ptr %a35
  br i1 %t34, label %rhs36, label %join37
rhs36:
  %t38 = load i64, ptr %a28
  %t39 = load i64, ptr %a9
  %t40 = icmp slt i64 %t38, %t39
  store i1 %t40, ptr %a35
  br label %join37
join37:
  %t41 = load i1, ptr %a35
  store i1 %t41, ptr %a42
  br i1 %t41, label %rhs43, label %join44
rhs43:
  %t45 = load %ax_arr, ptr %a1
  %t46 = load i64, ptr %a28
  %t47 = extractvalue %ax_arr %t45, 0
  %t48 = extractvalue %ax_arr %t45, 1
  %t49 = getelementptr inbounds i8, ptr %t47, i64 %t46
  %t50 = load i8, ptr %t49
  %t51 = icmp ne i8 %t50, 13
  store i1 %t51, ptr %a42
  br label %join44
join44:
  %t52 = load i1, ptr %a42
  store i1 %t52, ptr %a53
  br i1 %t52, label %rhs54, label %join55
rhs54:
  %t56 = load %ax_arr, ptr %a1
  %t57 = load i64, ptr %a28
  %t58 = extractvalue %ax_arr %t56, 0
  %t59 = extractvalue %ax_arr %t56, 1
  %t60 = getelementptr inbounds i8, ptr %t58, i64 %t57
  %t61 = load i8, ptr %t60
  %t62 = icmp ne i8 %t61, 10
  store i1 %t62, ptr %a53
  br label %join55
join55:
  %t63 = load i1, ptr %a53
  br i1 %t63, label %loop_body31, label %loop_exit32
loop_body31:
  %t64 = load i64, ptr %a28
  %t65 = add i64 %t64, 1
  %t66 = load %ax_arr, ptr %a1
  %t67 = insertvalue %ax_arr %t66, i64 0, 2
  %t68 = load i64, ptr %a28
  %t69 = load %ax_arr, ptr %a4
  %t70 = insertvalue %ax_arr %t69, i64 0, 2
  %t71 = call i1 @ax_rt_match_ci__par(%ax_arr %t67, i64 %t68, %ax_arr %t70)
  store i1 %t71, ptr %a72
  br i1 %t71, label %rhs73, label %join74
rhs73:
  %t75 = load i64, ptr %a28
  %t76 = load i64, ptr %a20
  %t77 = icmp eq i64 %t75, %t76
  store i1 %t77, ptr %a78
  br i1 %t77, label %join80, label %rhs79
rhs79:
  %t81 = load i64, ptr %a28
  %t82 = icmp sgt i64 %t81, 0
  store i1 %t82, ptr %a83
  br i1 %t82, label %rhs84, label %join85
rhs84:
  %t86 = load %ax_arr, ptr %a1
  %t87 = load i64, ptr %a28
  %t88 = sub i64 %t87, 1
  %t89 = extractvalue %ax_arr %t86, 0
  %t90 = extractvalue %ax_arr %t86, 1
  %t91 = getelementptr inbounds i8, ptr %t89, i64 %t88
  %t92 = load i8, ptr %t91
  %t93 = icmp eq i8 %t92, 32
  store i1 %t93, ptr %a94
  br i1 %t93, label %join96, label %rhs95
rhs95:
  %t97 = load %ax_arr, ptr %a1
  %t98 = load i64, ptr %a28
  %t99 = sub i64 %t98, 1
  %t100 = extractvalue %ax_arr %t97, 0
  %t101 = extractvalue %ax_arr %t97, 1
  %t102 = getelementptr inbounds i8, ptr %t100, i64 %t99
  %t103 = load i8, ptr %t102
  %t104 = icmp eq i8 %t103, 44
  store i1 %t104, ptr %a94
  br label %join96
join96:
  %t105 = load i1, ptr %a94
  store i1 %t105, ptr %a106
  br i1 %t105, label %join108, label %rhs107
rhs107:
  %t109 = load %ax_arr, ptr %a1
  %t110 = load i64, ptr %a28
  %t111 = sub i64 %t110, 1
  %t112 = extractvalue %ax_arr %t109, 0
  %t113 = extractvalue %ax_arr %t109, 1
  %t114 = getelementptr inbounds i8, ptr %t112, i64 %t111
  %t115 = load i8, ptr %t114
  %t116 = icmp eq i8 %t115, 9
  store i1 %t116, ptr %a106
  br label %join108
join108:
  %t117 = load i1, ptr %a106
  store i1 %t117, ptr %a83
  br label %join85
join85:
  %t118 = load i1, ptr %a83
  store i1 %t118, ptr %a78
  br label %join80
join80:
  %t119 = load i1, ptr %a78
  store i1 %t119, ptr %a72
  br label %join74
join74:
  %t120 = load i1, ptr %a72
  store i1 %t120, ptr %a121
  br i1 %t120, label %rhs122, label %join123
rhs122:
  %t124 = load i64, ptr %a28
  %t125 = load i64, ptr %a12
  %t126 = add i64 %t124, %t125
  %t127 = load i64, ptr %a9
  %t128 = icmp slt i64 %t126, %t127
  store i1 %t128, ptr %a121
  br label %join123
join123:
  %t129 = load i1, ptr %a121
  store i1 %t129, ptr %a130
  br i1 %t129, label %rhs131, label %join132
rhs131:
  %t133 = load %ax_arr, ptr %a1
  %t134 = load i64, ptr %a28
  %t135 = load i64, ptr %a12
  %t136 = add i64 %t134, %t135
  %t137 = extractvalue %ax_arr %t133, 0
  %t138 = extractvalue %ax_arr %t133, 1
  %t139 = getelementptr inbounds i8, ptr %t137, i64 %t136
  %t140 = load i8, ptr %t139
  %t141 = icmp eq i8 %t140, 13
  store i1 %t141, ptr %a142
  br i1 %t141, label %join144, label %rhs143
rhs143:
  %t145 = load %ax_arr, ptr %a1
  %t146 = load i64, ptr %a28
  %t147 = load i64, ptr %a12
  %t148 = add i64 %t146, %t147
  %t149 = extractvalue %ax_arr %t145, 0
  %t150 = extractvalue %ax_arr %t145, 1
  %t151 = getelementptr inbounds i8, ptr %t149, i64 %t148
  %t152 = load i8, ptr %t151
  %t153 = icmp eq i8 %t152, 32
  store i1 %t153, ptr %a142
  br label %join144
join144:
  %t154 = load i1, ptr %a142
  store i1 %t154, ptr %a155
  br i1 %t154, label %join157, label %rhs156
rhs156:
  %t158 = load %ax_arr, ptr %a1
  %t159 = load i64, ptr %a28
  %t160 = load i64, ptr %a12
  %t161 = add i64 %t159, %t160
  %t162 = extractvalue %ax_arr %t158, 0
  %t163 = extractvalue %ax_arr %t158, 1
  %t164 = getelementptr inbounds i8, ptr %t162, i64 %t161
  %t165 = load i8, ptr %t164
  %t166 = icmp eq i8 %t165, 44
  store i1 %t166, ptr %a155
  br label %join157
join157:
  %t167 = load i1, ptr %a155
  store i1 %t167, ptr %a168
  br i1 %t167, label %join170, label %rhs169
rhs169:
  %t171 = load %ax_arr, ptr %a1
  %t172 = load i64, ptr %a28
  %t173 = load i64, ptr %a12
  %t174 = add i64 %t172, %t173
  %t175 = extractvalue %ax_arr %t171, 0
  %t176 = extractvalue %ax_arr %t171, 1
  %t177 = getelementptr inbounds i8, ptr %t175, i64 %t174
  %t178 = load i8, ptr %t177
  %t179 = icmp eq i8 %t178, 9
  store i1 %t179, ptr %a168
  br label %join170
join170:
  %t180 = load i1, ptr %a168
  store i1 %t180, ptr %a130
  br label %join132
join132:
  %t181 = load i1, ptr %a130
  store i64 %t65, ptr %a28
  store i1 %t181, ptr %a29
  br label %loop_cond30
loop_exit32:
  %t182 = load i1, ptr %a29
  store i1 %t182, ptr %a23
  br label %join26
join26:
  %t183 = load i1, ptr %a23
  %t184 = load i64, ptr %a2
  %t185 = icmp ne i64 %t184, 0
  %t186 = load %ax_arr, ptr %a1
  br i1 %t185, label %free187, label %cont188
free187:
  %t189 = extractvalue %ax_arr %t186, 0
  %t190 = extractvalue %ax_arr %t186, 1
  %t191 = mul i64 %t190, 1
  call void @ax_free(ptr %t189, i64 %t191)
  br label %cont188
cont188:
  %t192 = load i64, ptr %a5
  %t193 = icmp ne i64 %t192, 0
  %t194 = load %ax_arr, ptr %a4
  br i1 %t193, label %free195, label %cont196
free195:
  %t197 = extractvalue %ax_arr %t194, 0
  %t198 = extractvalue %ax_arr %t194, 1
  %t199 = mul i64 %t198, 1
  call void @ax_free(ptr %t197, i64 %t199)
  br label %cont196
cont196:
  ret i1 %t183
}

; rt_connection_token  graph:cc007414139e27c6
define internal i1 @ax_rt_connection_token__seq(%ax_arr %p_headers, %ax_arr %p_token) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a20 = alloca i64
  %a23 = alloca i1
  %a28 = alloca i64
  %a29 = alloca i1
  %a35 = alloca i1
  %a42 = alloca i1
  %a53 = alloca i1
  %a72 = alloca i1
  %a78 = alloca i1
  %a83 = alloca i1
  %a94 = alloca i1
  %a106 = alloca i1
  %a121 = alloca i1
  %a130 = alloca i1
  %a142 = alloca i1
  %a155 = alloca i1
  %a168 = alloca i1
  store %ax_arr %p_headers, ptr %a1
  %t3 = extractvalue %ax_arr %p_headers, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_token, ptr %a4
  %t6 = extractvalue %ax_arr %p_token, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load %ax_arr, ptr %a1
  %t14 = insertvalue %ax_arr %t13, i64 0, 2
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.22, 0
  %t16 = insertvalue %ax_arr %t15, i64 11, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = insertvalue %ax_arr %t17, i64 0, 2
  %t19 = call i64 @ax_rt_header__seq(%ax_arr %t14, %ax_arr %t18, i64 0)
  store i64 %t19, ptr %a20
  %t21 = load i64, ptr %a20
  %t22 = icmp slt i64 %t21, 0
  br i1 %t22, label %then24, label %else25
then24:
  store i1 false, ptr %a23
  br label %join26
else25:
  %t27 = load i64, ptr %a20
  store i64 %t27, ptr %a28
  store i1 false, ptr %a29
  br label %loop_cond30
loop_cond30:
  %t33 = load i1, ptr %a29
  %t34 = xor i1 %t33, true
  store i1 %t34, ptr %a35
  br i1 %t34, label %rhs36, label %join37
rhs36:
  %t38 = load i64, ptr %a28
  %t39 = load i64, ptr %a9
  %t40 = icmp slt i64 %t38, %t39
  store i1 %t40, ptr %a35
  br label %join37
join37:
  %t41 = load i1, ptr %a35
  store i1 %t41, ptr %a42
  br i1 %t41, label %rhs43, label %join44
rhs43:
  %t45 = load %ax_arr, ptr %a1
  %t46 = load i64, ptr %a28
  %t47 = extractvalue %ax_arr %t45, 0
  %t48 = extractvalue %ax_arr %t45, 1
  %t49 = getelementptr inbounds i8, ptr %t47, i64 %t46
  %t50 = load i8, ptr %t49
  %t51 = icmp ne i8 %t50, 13
  store i1 %t51, ptr %a42
  br label %join44
join44:
  %t52 = load i1, ptr %a42
  store i1 %t52, ptr %a53
  br i1 %t52, label %rhs54, label %join55
rhs54:
  %t56 = load %ax_arr, ptr %a1
  %t57 = load i64, ptr %a28
  %t58 = extractvalue %ax_arr %t56, 0
  %t59 = extractvalue %ax_arr %t56, 1
  %t60 = getelementptr inbounds i8, ptr %t58, i64 %t57
  %t61 = load i8, ptr %t60
  %t62 = icmp ne i8 %t61, 10
  store i1 %t62, ptr %a53
  br label %join55
join55:
  %t63 = load i1, ptr %a53
  br i1 %t63, label %loop_body31, label %loop_exit32
loop_body31:
  %t64 = load i64, ptr %a28
  %t65 = add i64 %t64, 1
  %t66 = load %ax_arr, ptr %a1
  %t67 = insertvalue %ax_arr %t66, i64 0, 2
  %t68 = load i64, ptr %a28
  %t69 = load %ax_arr, ptr %a4
  %t70 = insertvalue %ax_arr %t69, i64 0, 2
  %t71 = call i1 @ax_rt_match_ci__seq(%ax_arr %t67, i64 %t68, %ax_arr %t70)
  store i1 %t71, ptr %a72
  br i1 %t71, label %rhs73, label %join74
rhs73:
  %t75 = load i64, ptr %a28
  %t76 = load i64, ptr %a20
  %t77 = icmp eq i64 %t75, %t76
  store i1 %t77, ptr %a78
  br i1 %t77, label %join80, label %rhs79
rhs79:
  %t81 = load i64, ptr %a28
  %t82 = icmp sgt i64 %t81, 0
  store i1 %t82, ptr %a83
  br i1 %t82, label %rhs84, label %join85
rhs84:
  %t86 = load %ax_arr, ptr %a1
  %t87 = load i64, ptr %a28
  %t88 = sub i64 %t87, 1
  %t89 = extractvalue %ax_arr %t86, 0
  %t90 = extractvalue %ax_arr %t86, 1
  %t91 = getelementptr inbounds i8, ptr %t89, i64 %t88
  %t92 = load i8, ptr %t91
  %t93 = icmp eq i8 %t92, 32
  store i1 %t93, ptr %a94
  br i1 %t93, label %join96, label %rhs95
rhs95:
  %t97 = load %ax_arr, ptr %a1
  %t98 = load i64, ptr %a28
  %t99 = sub i64 %t98, 1
  %t100 = extractvalue %ax_arr %t97, 0
  %t101 = extractvalue %ax_arr %t97, 1
  %t102 = getelementptr inbounds i8, ptr %t100, i64 %t99
  %t103 = load i8, ptr %t102
  %t104 = icmp eq i8 %t103, 44
  store i1 %t104, ptr %a94
  br label %join96
join96:
  %t105 = load i1, ptr %a94
  store i1 %t105, ptr %a106
  br i1 %t105, label %join108, label %rhs107
rhs107:
  %t109 = load %ax_arr, ptr %a1
  %t110 = load i64, ptr %a28
  %t111 = sub i64 %t110, 1
  %t112 = extractvalue %ax_arr %t109, 0
  %t113 = extractvalue %ax_arr %t109, 1
  %t114 = getelementptr inbounds i8, ptr %t112, i64 %t111
  %t115 = load i8, ptr %t114
  %t116 = icmp eq i8 %t115, 9
  store i1 %t116, ptr %a106
  br label %join108
join108:
  %t117 = load i1, ptr %a106
  store i1 %t117, ptr %a83
  br label %join85
join85:
  %t118 = load i1, ptr %a83
  store i1 %t118, ptr %a78
  br label %join80
join80:
  %t119 = load i1, ptr %a78
  store i1 %t119, ptr %a72
  br label %join74
join74:
  %t120 = load i1, ptr %a72
  store i1 %t120, ptr %a121
  br i1 %t120, label %rhs122, label %join123
rhs122:
  %t124 = load i64, ptr %a28
  %t125 = load i64, ptr %a12
  %t126 = add i64 %t124, %t125
  %t127 = load i64, ptr %a9
  %t128 = icmp slt i64 %t126, %t127
  store i1 %t128, ptr %a121
  br label %join123
join123:
  %t129 = load i1, ptr %a121
  store i1 %t129, ptr %a130
  br i1 %t129, label %rhs131, label %join132
rhs131:
  %t133 = load %ax_arr, ptr %a1
  %t134 = load i64, ptr %a28
  %t135 = load i64, ptr %a12
  %t136 = add i64 %t134, %t135
  %t137 = extractvalue %ax_arr %t133, 0
  %t138 = extractvalue %ax_arr %t133, 1
  %t139 = getelementptr inbounds i8, ptr %t137, i64 %t136
  %t140 = load i8, ptr %t139
  %t141 = icmp eq i8 %t140, 13
  store i1 %t141, ptr %a142
  br i1 %t141, label %join144, label %rhs143
rhs143:
  %t145 = load %ax_arr, ptr %a1
  %t146 = load i64, ptr %a28
  %t147 = load i64, ptr %a12
  %t148 = add i64 %t146, %t147
  %t149 = extractvalue %ax_arr %t145, 0
  %t150 = extractvalue %ax_arr %t145, 1
  %t151 = getelementptr inbounds i8, ptr %t149, i64 %t148
  %t152 = load i8, ptr %t151
  %t153 = icmp eq i8 %t152, 32
  store i1 %t153, ptr %a142
  br label %join144
join144:
  %t154 = load i1, ptr %a142
  store i1 %t154, ptr %a155
  br i1 %t154, label %join157, label %rhs156
rhs156:
  %t158 = load %ax_arr, ptr %a1
  %t159 = load i64, ptr %a28
  %t160 = load i64, ptr %a12
  %t161 = add i64 %t159, %t160
  %t162 = extractvalue %ax_arr %t158, 0
  %t163 = extractvalue %ax_arr %t158, 1
  %t164 = getelementptr inbounds i8, ptr %t162, i64 %t161
  %t165 = load i8, ptr %t164
  %t166 = icmp eq i8 %t165, 44
  store i1 %t166, ptr %a155
  br label %join157
join157:
  %t167 = load i1, ptr %a155
  store i1 %t167, ptr %a168
  br i1 %t167, label %join170, label %rhs169
rhs169:
  %t171 = load %ax_arr, ptr %a1
  %t172 = load i64, ptr %a28
  %t173 = load i64, ptr %a12
  %t174 = add i64 %t172, %t173
  %t175 = extractvalue %ax_arr %t171, 0
  %t176 = extractvalue %ax_arr %t171, 1
  %t177 = getelementptr inbounds i8, ptr %t175, i64 %t174
  %t178 = load i8, ptr %t177
  %t179 = icmp eq i8 %t178, 9
  store i1 %t179, ptr %a168
  br label %join170
join170:
  %t180 = load i1, ptr %a168
  store i1 %t180, ptr %a130
  br label %join132
join132:
  %t181 = load i1, ptr %a130
  store i64 %t65, ptr %a28
  store i1 %t181, ptr %a29
  br label %loop_cond30
loop_exit32:
  %t182 = load i1, ptr %a29
  store i1 %t182, ptr %a23
  br label %join26
join26:
  %t183 = load i1, ptr %a23
  %t184 = load i64, ptr %a2
  %t185 = icmp ne i64 %t184, 0
  %t186 = load %ax_arr, ptr %a1
  br i1 %t185, label %free187, label %cont188
free187:
  %t189 = extractvalue %ax_arr %t186, 0
  %t190 = extractvalue %ax_arr %t186, 1
  %t191 = mul i64 %t190, 1
  call void @ax_free(ptr %t189, i64 %t191)
  br label %cont188
cont188:
  %t192 = load i64, ptr %a5
  %t193 = icmp ne i64 %t192, 0
  %t194 = load %ax_arr, ptr %a4
  br i1 %t193, label %free195, label %cont196
free195:
  %t197 = extractvalue %ax_arr %t194, 0
  %t198 = extractvalue %ax_arr %t194, 1
  %t199 = mul i64 %t198, 1
  call void @ax_free(ptr %t197, i64 %t199)
  br label %cont196
cont196:
  ret i1 %t183
}

; rt_drop  graph:aeda18febdf5c569
define internal void @ax_rt_drop__seq(ptr %p_state) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a5 = alloca i64
  %a8 = alloca i8
  %a14 = alloca i64
  %a18 = alloca i8
  %a22 = alloca i8
  %a26 = alloca ptr
  store ptr %p_state, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = getelementptr i8, ptr %t2, i64 0
  %t4 = load i64, ptr %t3, align 1
  store i64 %t4, ptr %a5
  %t6 = load i64, ptr %a5
  %t7 = icmp slt i64 %t6, 0
  br i1 %t7, label %then9, label %else10
then9:
  store i8 0, ptr %a8
  br label %join11
else10:
  %t12 = load i64, ptr %a5
  %t13 = call i64 @ax_rt_close__seq(i64 %t12)
  store i64 %t13, ptr %a14
  %t15 = load ptr, ptr %a1
  %t16 = getelementptr i8, ptr %t15, i64 8
  %t17 = load ptr, ptr %t16, align 1
  call void @ax_ax_release__seq(ptr %t17)
  store i8 0, ptr %a18
  %t19 = load ptr, ptr %a1
  %t20 = getelementptr i8, ptr %t19, i64 24
  %t21 = load ptr, ptr %t20, align 1
  call void @ax_ax_release__seq(ptr %t21)
  store i8 0, ptr %a22
  %t23 = load ptr, ptr %a1
  %t24 = trunc i64 0 to i32
  %t25 = call ptr @memset(ptr %t23, i32 %t24, i64 64)
  store ptr %t25, ptr %a26
  %t27 = load ptr, ptr %a1
  %t28 = getelementptr i8, ptr %t27, i64 0
  store i64 -1, ptr %t28, align 1
  store i8 0, ptr %a8
  br label %join11
join11:
  %t29 = load i8, ptr %a8
  ret void
}

; rt_request  graph:b3c08e2c85424970
define internal i64 @ax_rt_request__seq(ptr %p_state, ptr %p_handler, ptr %p_input, i64 %p_n, i64 %p_offset) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca i64
  %a8 = alloca i1
  %a26 = alloca %ax_arr
  %a27 = alloca i64
  %a36 = alloca i64
  %a39 = alloca i64
  %a47 = alloca i8
  %a53 = alloca i8
  %a56 = alloca i64
  %a59 = alloca i1
  %a77 = alloca %ax_arr
  %a78 = alloca i64
  %a82 = alloca i64
  %a85 = alloca i1
  %a93 = alloca i64
  %a98 = alloca i8
  %a102 = alloca i64
  %a108 = alloca i64
  %a122 = alloca %ax_arr
  %a123 = alloca i64
  %a127 = alloca i64
  %a132 = alloca i8
  %a136 = alloca ptr
  %a140 = alloca i64
  %a144 = alloca i64
  %a151 = alloca i8
  %a160 = alloca ptr
  %a165 = alloca ptr
  %a167 = alloca i8
  %a172 = alloca i8
  %a183 = alloca ptr
  %a190 = alloca i8
  %a199 = alloca i1
  %a210 = alloca i1
  %a223 = alloca i64
  %a229 = alloca i8
  store ptr %p_state, ptr %a1
  store ptr %p_handler, ptr %a2
  store ptr %p_input, ptr %a3
  store i64 %p_n, ptr %a4
  store i64 %p_offset, ptr %a5
  %t6 = load i64, ptr %a5
  %t7 = icmp sge i64 %t6, 0
  store i1 %t7, ptr %a8
  br i1 %t7, label %rhs9, label %join10
rhs9:
  %t11 = load i64, ptr %a5
  %t12 = load i64, ptr %a4
  %t13 = icmp sle i64 %t11, %t12
  store i1 %t13, ptr %a8
  br label %join10
join10:
  %t14 = load i1, ptr %a8
  br i1 %t14, label %chk_ok15, label %chk_fail16
chk_fail16:
  call void @ax_trap(ptr @.str.1)
  unreachable
chk_ok15:
  %t17 = load ptr, ptr %a3
  %t18 = load i64, ptr %a5
  %t19 = getelementptr i8, ptr %t17, i64 %t18
  %t20 = load i64, ptr %a4
  %t21 = load i64, ptr %a5
  %t22 = sub i64 %t20, %t21
  %t23 = insertvalue %ax_arr undef, ptr %t19, 0
  %t24 = insertvalue %ax_arr %t23, i64 %t22, 1
  %t25 = insertvalue %ax_arr %t24, i64 0, 2
  store %ax_arr %t25, ptr %a26
  store i64 0, ptr %a27
  %t28 = load %ax_arr, ptr %a26
  %t29 = load i64, ptr %a27
  store i64 0, ptr %a27
  %t30 = insertvalue %ax_arr %t28, i64 %t29, 2
  %t31 = insertvalue %ax_arr undef, ptr @.bytes.23, 0
  %t32 = insertvalue %ax_arr %t31, i64 4, 1
  %t33 = insertvalue %ax_arr %t32, i64 0, 2
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = call i64 @ax_rt_find__seq(%ax_arr %t30, %ax_arr %t34, i64 0)
  store i64 %t35, ptr %a36
  %t37 = load i64, ptr %a36
  %t38 = icmp slt i64 %t37, 0
  br i1 %t38, label %then40, label %else41
then40:
  %t43 = load i64, ptr %a4
  %t44 = load i64, ptr %a5
  %t45 = sub i64 %t43, %t44
  %t46 = icmp eq i64 %t45, 65536
  br i1 %t46, label %then48, label %else49
then48:
  %t51 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t51)
  store i8 0, ptr %a47
  br label %join50
else49:
  store i8 0, ptr %a47
  br label %join50
join50:
  %t52 = load i8, ptr %a47
  store i8 %t52, ptr %a53
  store i64 0, ptr %a39
  br label %join42
else41:
  %t54 = load i64, ptr %a36
  %t55 = add i64 %t54, 4
  store i64 %t55, ptr %a56
  %t57 = load i64, ptr %a56
  %t58 = icmp sge i64 %t57, 0
  store i1 %t58, ptr %a59
  br i1 %t58, label %rhs60, label %join61
rhs60:
  %t62 = load i64, ptr %a56
  %t63 = load i64, ptr %a4
  %t64 = load i64, ptr %a5
  %t65 = sub i64 %t63, %t64
  %t66 = icmp sle i64 %t62, %t65
  store i1 %t66, ptr %a59
  br label %join61
join61:
  %t67 = load i1, ptr %a59
  br i1 %t67, label %chk_ok68, label %chk_fail69
chk_fail69:
  call void @ax_trap(ptr @.str.2)
  unreachable
chk_ok68:
  %t70 = load ptr, ptr %a3
  %t71 = load i64, ptr %a5
  %t72 = getelementptr i8, ptr %t70, i64 %t71
  %t73 = load i64, ptr %a56
  %t74 = insertvalue %ax_arr undef, ptr %t72, 0
  %t75 = insertvalue %ax_arr %t74, i64 %t73, 1
  %t76 = insertvalue %ax_arr %t75, i64 0, 2
  store %ax_arr %t76, ptr %a77
  store i64 0, ptr %a78
  %t79 = load %ax_arr, ptr %a77
  %t80 = insertvalue %ax_arr %t79, i64 0, 2
  %t81 = call i64 @ax_rt_body_length__seq(%ax_arr %t80)
  store i64 %t81, ptr %a82
  %t83 = load i64, ptr %a82
  %t84 = icmp slt i64 %t83, 0
  store i1 %t84, ptr %a85
  br i1 %t84, label %join87, label %rhs86
rhs86:
  %t88 = load i64, ptr %a56
  %t89 = load i64, ptr %a82
  %t90 = add i64 %t88, %t89
  %t91 = icmp sgt i64 %t90, 65536
  store i1 %t91, ptr %a85
  br label %join87
join87:
  %t92 = load i1, ptr %a85
  br i1 %t92, label %then94, label %else95
then94:
  %t97 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t97)
  store i8 0, ptr %a98
  store i64 0, ptr %a93
  br label %join96
else95:
  %t99 = load i64, ptr %a56
  %t100 = load i64, ptr %a82
  %t101 = add i64 %t99, %t100
  store i64 %t101, ptr %a102
  %t103 = load i64, ptr %a102
  %t104 = load i64, ptr %a4
  %t105 = load i64, ptr %a5
  %t106 = sub i64 %t104, %t105
  %t107 = icmp sgt i64 %t103, %t106
  br i1 %t107, label %then109, label %else110
then109:
  store i64 0, ptr %a108
  br label %join111
else110:
  %t112 = load ptr, ptr %a2
  %t113 = load ptr, ptr %a3
  %t114 = load i64, ptr %a5
  %t115 = getelementptr i8, ptr %t113, i64 %t114
  %t116 = load i64, ptr %a102
  %t117 = insertvalue %ax_arr undef, ptr %t115, 0
  %t118 = insertvalue %ax_arr %t117, i64 %t116, 1
  %t119 = insertvalue %ax_arr %t118, i64 0, 2
  %t120 = call %ax_arr %t112(%ax_arr %t119)
  %t121 = extractvalue %ax_arr %t120, 2
  store %ax_arr %t120, ptr %a122
  store i64 %t121, ptr %a123
  %t124 = load %ax_arr, ptr %a122
  %t125 = extractvalue %ax_arr %t124, 1
  %t126 = icmp eq i64 %t125, 0
  br i1 %t126, label %then128, label %else129
then128:
  %t131 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t131)
  store i8 0, ptr %a132
  store i64 0, ptr %a127
  br label %join130
else129:
  %t133 = load ptr, ptr %a1
  %t134 = getelementptr i8, ptr %t133, i64 24
  %t135 = load ptr, ptr %t134, align 1
  store ptr %t135, ptr %a136
  %t137 = load ptr, ptr %a1
  %t138 = getelementptr i8, ptr %t137, i64 32
  %t139 = load i64, ptr %t138, align 1
  store i64 %t139, ptr %a140
  %t141 = load ptr, ptr %a136
  %t142 = getelementptr i8, ptr %t141, i64 -16
  %t143 = load i64, ptr %t142, align 1
  store i64 %t143, ptr %a144
  %t145 = load i64, ptr %a140
  %t146 = load %ax_arr, ptr %a122
  %t147 = extractvalue %ax_arr %t146, 1
  %t148 = add i64 %t145, %t147
  %t149 = load i64, ptr %a144
  %t150 = icmp sgt i64 %t148, %t149
  br i1 %t150, label %then152, label %else153
then152:
  %t155 = load i64, ptr %a140
  %t156 = load %ax_arr, ptr %a122
  %t157 = extractvalue %ax_arr %t156, 1
  %t158 = add i64 %t155, %t157
  %t159 = call ptr @ax_alloc(i64 %t158)
  store ptr %t159, ptr %a160
  %t161 = load ptr, ptr %a160
  %t162 = load ptr, ptr %a136
  %t163 = load i64, ptr %a140
  %t164 = call ptr @memcpy(ptr %t161, ptr %t162, i64 %t163)
  store ptr %t164, ptr %a165
  %t166 = load ptr, ptr %a136
  call void @ax_ax_release__seq(ptr %t166)
  store i8 0, ptr %a167
  %t168 = load ptr, ptr %a1
  %t169 = load ptr, ptr %a160
  %t170 = getelementptr i8, ptr %t168, i64 24
  store ptr %t169, ptr %t170, align 1
  store i8 0, ptr %a151
  br label %join154
else153:
  store i8 0, ptr %a151
  br label %join154
join154:
  %t171 = load i8, ptr %a151
  store i8 %t171, ptr %a172
  %t173 = load ptr, ptr %a1
  %t174 = getelementptr i8, ptr %t173, i64 24
  %t175 = load ptr, ptr %t174, align 1
  %t176 = load i64, ptr %a140
  %t177 = getelementptr i8, ptr %t175, i64 %t176
  %t178 = load %ax_arr, ptr %a122
  %t179 = extractvalue %ax_arr %t178, 0
  %t180 = load %ax_arr, ptr %a122
  %t181 = extractvalue %ax_arr %t180, 1
  %t182 = call ptr @memcpy(ptr %t177, ptr %t179, i64 %t181)
  store ptr %t182, ptr %a183
  %t184 = load ptr, ptr %a1
  %t185 = load i64, ptr %a140
  %t186 = load %ax_arr, ptr %a122
  %t187 = extractvalue %ax_arr %t186, 1
  %t188 = add i64 %t185, %t187
  %t189 = getelementptr i8, ptr %t184, i64 32
  store i64 %t188, ptr %t189, align 1
  store i8 0, ptr %a190
  %t191 = load ptr, ptr %a1
  %t192 = load %ax_arr, ptr %a77
  %t193 = insertvalue %ax_arr %t192, i64 0, 2
  %t194 = insertvalue %ax_arr undef, ptr @.bytes.24, 0
  %t195 = insertvalue %ax_arr %t194, i64 5, 1
  %t196 = insertvalue %ax_arr %t195, i64 0, 2
  %t197 = insertvalue %ax_arr %t196, i64 0, 2
  %t198 = call i1 @ax_rt_connection_token__seq(%ax_arr %t193, %ax_arr %t197)
  store i1 %t198, ptr %a199
  br i1 %t198, label %join201, label %rhs200
rhs200:
  %t202 = load %ax_arr, ptr %a77
  %t203 = insertvalue %ax_arr %t202, i64 0, 2
  %t204 = insertvalue %ax_arr undef, ptr @.bytes.25, 0
  %t205 = insertvalue %ax_arr %t204, i64 8, 1
  %t206 = insertvalue %ax_arr %t205, i64 0, 2
  %t207 = insertvalue %ax_arr %t206, i64 0, 2
  %t208 = call i64 @ax_rt_find__seq(%ax_arr %t203, %ax_arr %t207, i64 0)
  %t209 = icmp sge i64 %t208, 0
  store i1 %t209, ptr %a210
  br i1 %t209, label %rhs211, label %join212
rhs211:
  %t213 = load %ax_arr, ptr %a77
  %t214 = insertvalue %ax_arr %t213, i64 0, 2
  %t215 = insertvalue %ax_arr undef, ptr @.bytes.26, 0
  %t216 = insertvalue %ax_arr %t215, i64 10, 1
  %t217 = insertvalue %ax_arr %t216, i64 0, 2
  %t218 = insertvalue %ax_arr %t217, i64 0, 2
  %t219 = call i1 @ax_rt_connection_token__seq(%ax_arr %t214, %ax_arr %t218)
  %t220 = xor i1 %t219, true
  store i1 %t220, ptr %a210
  br label %join212
join212:
  %t221 = load i1, ptr %a210
  store i1 %t221, ptr %a199
  br label %join201
join201:
  %t222 = load i1, ptr %a199
  br i1 %t222, label %then224, label %else225
then224:
  store i64 1, ptr %a223
  br label %join226
else225:
  store i64 0, ptr %a223
  br label %join226
join226:
  %t227 = load i64, ptr %a223
  %t228 = getelementptr i8, ptr %t191, i64 48
  store i64 %t227, ptr %t228, align 1
  store i8 0, ptr %a229
  %t230 = load i64, ptr %a102
  store i64 %t230, ptr %a127
  br label %join130
join130:
  %t231 = load i64, ptr %a127
  %t232 = load i64, ptr %a123
  %t233 = icmp ne i64 %t232, 0
  %t234 = load %ax_arr, ptr %a122
  br i1 %t233, label %free235, label %cont236
free235:
  %t237 = extractvalue %ax_arr %t234, 0
  %t238 = extractvalue %ax_arr %t234, 1
  %t239 = mul i64 %t238, 1
  call void @ax_free(ptr %t237, i64 %t239)
  br label %cont236
cont236:
  store i64 %t231, ptr %a108
  br label %join111
join111:
  %t240 = load i64, ptr %a108
  store i64 %t240, ptr %a93
  br label %join96
join96:
  %t241 = load i64, ptr %a93
  %t242 = load i64, ptr %a78
  %t243 = icmp ne i64 %t242, 0
  %t244 = load %ax_arr, ptr %a77
  br i1 %t243, label %free245, label %cont246
free245:
  %t247 = extractvalue %ax_arr %t244, 0
  %t248 = extractvalue %ax_arr %t244, 1
  %t249 = mul i64 %t248, 1
  call void @ax_free(ptr %t247, i64 %t249)
  br label %cont246
cont246:
  store i64 %t241, ptr %a39
  br label %join42
join42:
  %t250 = load i64, ptr %a39
  %t251 = load i64, ptr %a27
  %t252 = icmp ne i64 %t251, 0
  %t253 = load %ax_arr, ptr %a26
  br i1 %t252, label %free254, label %cont255
free254:
  %t256 = extractvalue %ax_arr %t253, 0
  %t257 = extractvalue %ax_arr %t253, 1
  %t258 = mul i64 %t257, 1
  call void @ax_free(ptr %t256, i64 %t258)
  br label %cont255
cont255:
  ret i64 %t250
}

; rt_batch_next  graph:11dcb6b313a1b502
define internal { i64, i1, i64 } @ax_rt_batch_next__seq(ptr %p_state, ptr %p_handler, ptr %p_input, i64 %p_n, { i64, i1, i64 } %p_batch) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca { i64, i1, i64 }
  %a13 = alloca i64
  %a21 = alloca i1
  %a29 = alloca i1
  store ptr %p_state, ptr %a1
  store ptr %p_handler, ptr %a2
  store ptr %p_input, ptr %a3
  store i64 %p_n, ptr %a4
  store { i64, i1, i64 } %p_batch, ptr %a5
  %t6 = load ptr, ptr %a1
  %t7 = load ptr, ptr %a2
  %t8 = load ptr, ptr %a3
  %t9 = load i64, ptr %a4
  %t10 = load { i64, i1, i64 }, ptr %a5
  %t11 = extractvalue { i64, i1, i64 } %t10, 0
  %t12 = call i64 @ax_rt_request__seq(ptr %t6, ptr %t7, ptr %t8, i64 %t9, i64 %t11)
  store i64 %t12, ptr %a13
  %t14 = load { i64, i1, i64 }, ptr %a5
  %t15 = extractvalue { i64, i1, i64 } %t14, 0
  %t16 = load i64, ptr %a13
  %t17 = add i64 %t15, %t16
  %t18 = insertvalue { i64, i1, i64 } undef, i64 %t17, 0
  %t19 = load i64, ptr %a13
  %t20 = icmp sgt i64 %t19, 0
  store i1 %t20, ptr %a21
  br i1 %t20, label %rhs22, label %join23
rhs22:
  %t24 = load ptr, ptr %a1
  %t25 = getelementptr i8, ptr %t24, i64 0
  %t26 = load i64, ptr %t25, align 1
  %t27 = icmp sge i64 %t26, 0
  store i1 %t27, ptr %a21
  br label %join23
join23:
  %t28 = load i1, ptr %a21
  store i1 %t28, ptr %a29
  br i1 %t28, label %rhs30, label %join31
rhs30:
  %t32 = load ptr, ptr %a1
  %t33 = getelementptr i8, ptr %t32, i64 48
  %t34 = load i64, ptr %t33, align 1
  %t35 = icmp eq i64 %t34, 0
  store i1 %t35, ptr %a29
  br label %join31
join31:
  %t36 = load i1, ptr %a29
  %t37 = insertvalue { i64, i1, i64 } %t18, i1 %t36, 1
  %t38 = load { i64, i1, i64 }, ptr %a5
  %t39 = extractvalue { i64, i1, i64 } %t38, 2
  %t40 = add i64 %t39, 1
  %t41 = insertvalue { i64, i1, i64 } %t37, i64 %t40, 2
  ret { i64, i1, i64 } %t41
}

; rt_prepare  graph:5f0b04e7f49d28f5
define internal void @ax_rt_prepare__seq(ptr %p_state, ptr %p_handler) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a6 = alloca i64
  %a9 = alloca i1
  %a20 = alloca ptr
  %a23 = alloca i8
  %a27 = alloca { i64, i1, i64 }
  %a33 = alloca i1
  %a41 = alloca i1
  %a48 = alloca i1
  %a63 = alloca { i64, i1, i64 }
  %a68 = alloca i8
  %a82 = alloca ptr
  %a89 = alloca i8
  %a93 = alloca i1
  %a101 = alloca i64
  store ptr %p_state, ptr %a1
  store ptr %p_handler, ptr %a2
  %t3 = load ptr, ptr %a1
  %t4 = getelementptr i8, ptr %t3, i64 16
  %t5 = load i64, ptr %t4, align 1
  store i64 %t5, ptr %a6
  %t7 = load i64, ptr %a6
  %t8 = icmp sge i64 %t7, 0
  store i1 %t8, ptr %a9
  br i1 %t8, label %rhs10, label %join11
rhs10:
  %t12 = load i64, ptr %a6
  %t13 = icmp sle i64 %t12, 65536
  store i1 %t13, ptr %a9
  br label %join11
join11:
  %t14 = load i1, ptr %a9
  br i1 %t14, label %chk_ok15, label %chk_fail16
chk_fail16:
  call void @ax_trap(ptr @.str.3)
  unreachable
chk_ok15:
  %t17 = load ptr, ptr %a1
  %t18 = getelementptr i8, ptr %t17, i64 8
  %t19 = load ptr, ptr %t18, align 1
  store ptr %t19, ptr %a20
  %t21 = load ptr, ptr %a1
  %t22 = getelementptr i8, ptr %t21, i64 56
  store i64 0, ptr %t22, align 1
  store i8 0, ptr %a23
  %t24 = insertvalue { i64, i1, i64 } undef, i64 0, 0
  %t25 = insertvalue { i64, i1, i64 } %t24, i1 true, 1
  %t26 = insertvalue { i64, i1, i64 } %t25, i64 0, 2
  store { i64, i1, i64 } %t26, ptr %a27
  br label %loop_cond28
loop_cond28:
  %t31 = load { i64, i1, i64 }, ptr %a27
  %t32 = extractvalue { i64, i1, i64 } %t31, 1
  store i1 %t32, ptr %a33
  br i1 %t32, label %rhs34, label %join35
rhs34:
  %t36 = load { i64, i1, i64 }, ptr %a27
  %t37 = extractvalue { i64, i1, i64 } %t36, 0
  %t38 = load i64, ptr %a6
  %t39 = icmp slt i64 %t37, %t38
  store i1 %t39, ptr %a33
  br label %join35
join35:
  %t40 = load i1, ptr %a33
  store i1 %t40, ptr %a41
  br i1 %t40, label %rhs42, label %join43
rhs42:
  %t44 = load { i64, i1, i64 }, ptr %a27
  %t45 = extractvalue { i64, i1, i64 } %t44, 2
  %t46 = icmp slt i64 %t45, 64
  store i1 %t46, ptr %a41
  br label %join43
join43:
  %t47 = load i1, ptr %a41
  store i1 %t47, ptr %a48
  br i1 %t47, label %rhs49, label %join50
rhs49:
  %t51 = load ptr, ptr %a1
  %t52 = getelementptr i8, ptr %t51, i64 32
  %t53 = load i64, ptr %t52, align 1
  %t54 = icmp slt i64 %t53, 262144
  store i1 %t54, ptr %a48
  br label %join50
join50:
  %t55 = load i1, ptr %a48
  br i1 %t55, label %loop_body29, label %loop_exit30
loop_body29:
  %t56 = load ptr, ptr %a1
  %t57 = load ptr, ptr %a2
  %t58 = load ptr, ptr %a20
  %t59 = load i64, ptr %a6
  %t60 = load { i64, i1, i64 }, ptr %a27
  %t61 = call { i64, i1, i64 } @ax_rt_batch_next__seq(ptr %t56, ptr %t57, ptr %t58, i64 %t59, { i64, i1, i64 } %t60)
  store { i64, i1, i64 } %t61, ptr %a27
  br label %loop_cond28
loop_exit30:
  %t62 = load { i64, i1, i64 }, ptr %a27
  store { i64, i1, i64 } %t62, ptr %a63
  %t64 = load ptr, ptr %a1
  %t65 = getelementptr i8, ptr %t64, i64 0
  %t66 = load i64, ptr %t65, align 1
  %t67 = icmp slt i64 %t66, 0
  br i1 %t67, label %then69, label %else70
then69:
  store i8 0, ptr %a68
  br label %join71
else70:
  %t72 = load ptr, ptr %a20
  %t73 = load ptr, ptr %a20
  %t74 = load { i64, i1, i64 }, ptr %a63
  %t75 = extractvalue { i64, i1, i64 } %t74, 0
  %t76 = getelementptr i8, ptr %t73, i64 %t75
  %t77 = load i64, ptr %a6
  %t78 = load { i64, i1, i64 }, ptr %a63
  %t79 = extractvalue { i64, i1, i64 } %t78, 0
  %t80 = sub i64 %t77, %t79
  %t81 = call ptr @memmove(ptr %t72, ptr %t76, i64 %t80)
  store ptr %t81, ptr %a82
  %t83 = load ptr, ptr %a1
  %t84 = load i64, ptr %a6
  %t85 = load { i64, i1, i64 }, ptr %a63
  %t86 = extractvalue { i64, i1, i64 } %t85, 0
  %t87 = sub i64 %t84, %t86
  %t88 = getelementptr i8, ptr %t83, i64 16
  store i64 %t87, ptr %t88, align 1
  store i8 0, ptr %a89
  %t90 = load ptr, ptr %a1
  %t91 = load { i64, i1, i64 }, ptr %a63
  %t92 = extractvalue { i64, i1, i64 } %t91, 1
  store i1 %t92, ptr %a93
  br i1 %t92, label %rhs94, label %join95
rhs94:
  %t96 = load { i64, i1, i64 }, ptr %a63
  %t97 = extractvalue { i64, i1, i64 } %t96, 0
  %t98 = load i64, ptr %a6
  %t99 = icmp slt i64 %t97, %t98
  store i1 %t99, ptr %a93
  br label %join95
join95:
  %t100 = load i1, ptr %a93
  br i1 %t100, label %then102, label %else103
then102:
  store i64 1, ptr %a101
  br label %join104
else103:
  store i64 0, ptr %a101
  br label %join104
join104:
  %t105 = load i64, ptr %a101
  %t106 = getelementptr i8, ptr %t90, i64 56
  store i64 %t105, ptr %t106, align 1
  store i8 0, ptr %a68
  br label %join71
join71:
  %t107 = load i8, ptr %a68
  ret void
}

; rt_flush  graph:d61f6e70d14fccf1
define internal void @ax_rt_flush__seq(ptr %p_state) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a5 = alloca i64
  %a9 = alloca i64
  %a22 = alloca i64
  %a25 = alloca i8
  %a30 = alloca i8
  %a38 = alloca i8
  %a46 = alloca i64
  %a50 = alloca i8
  %a59 = alloca i8
  %a62 = alloca i8
  %a67 = alloca i8
  store ptr %p_state, ptr %a1
  %t2 = load ptr, ptr %a1
  %t3 = getelementptr i8, ptr %t2, i64 32
  %t4 = load i64, ptr %t3, align 1
  store i64 %t4, ptr %a5
  %t6 = load ptr, ptr %a1
  %t7 = getelementptr i8, ptr %t6, i64 40
  %t8 = load i64, ptr %t7, align 1
  store i64 %t8, ptr %a9
  %t10 = load ptr, ptr %a1
  %t11 = getelementptr i8, ptr %t10, i64 0
  %t12 = load i64, ptr %t11, align 1
  %t13 = load ptr, ptr %a1
  %t14 = getelementptr i8, ptr %t13, i64 24
  %t15 = load ptr, ptr %t14, align 1
  %t16 = load i64, ptr %a9
  %t17 = getelementptr i8, ptr %t15, i64 %t16
  %t18 = load i64, ptr %a5
  %t19 = load i64, ptr %a9
  %t20 = sub i64 %t18, %t19
  %t21 = call i64 @ax_rt_send__seq(i64 %t12, ptr %t17, i64 %t20)
  store i64 %t21, ptr %a22
  %t23 = load i64, ptr %a22
  %t24 = icmp slt i64 %t23, 0
  br i1 %t24, label %then26, label %else27
then26:
  %t29 = call i1 @ax_rt_retry__seq()
  br i1 %t29, label %then31, label %else32
then31:
  store i8 0, ptr %a30
  br label %join33
else32:
  %t34 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t34)
  store i8 0, ptr %a30
  br label %join33
join33:
  %t35 = load i8, ptr %a30
  store i8 %t35, ptr %a25
  br label %join28
else27:
  %t36 = load i64, ptr %a22
  %t37 = icmp eq i64 %t36, 0
  br i1 %t37, label %then39, label %else40
then39:
  %t42 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t42)
  store i8 0, ptr %a38
  br label %join41
else40:
  %t43 = load i64, ptr %a9
  %t44 = load i64, ptr %a22
  %t45 = add i64 %t43, %t44
  store i64 %t45, ptr %a46
  %t47 = load i64, ptr %a46
  %t48 = load i64, ptr %a5
  %t49 = icmp slt i64 %t47, %t48
  br i1 %t49, label %then51, label %else52
then51:
  %t54 = load ptr, ptr %a1
  %t55 = load i64, ptr %a46
  %t56 = getelementptr i8, ptr %t54, i64 40
  store i64 %t55, ptr %t56, align 1
  store i8 0, ptr %a50
  br label %join53
else52:
  %t57 = load ptr, ptr %a1
  %t58 = getelementptr i8, ptr %t57, i64 32
  store i64 0, ptr %t58, align 1
  store i8 0, ptr %a59
  %t60 = load ptr, ptr %a1
  %t61 = getelementptr i8, ptr %t60, i64 40
  store i64 0, ptr %t61, align 1
  store i8 0, ptr %a62
  %t63 = load ptr, ptr %a1
  %t64 = getelementptr i8, ptr %t63, i64 48
  %t65 = load i64, ptr %t64, align 1
  %t66 = icmp eq i64 %t65, 1
  br i1 %t66, label %then68, label %else69
then68:
  %t71 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t71)
  store i8 0, ptr %a67
  br label %join70
else69:
  store i8 0, ptr %a67
  br label %join70
join70:
  %t72 = load i8, ptr %a67
  store i8 %t72, ptr %a50
  br label %join53
join53:
  %t73 = load i8, ptr %a50
  store i8 %t73, ptr %a38
  br label %join41
join41:
  %t74 = load i8, ptr %a38
  store i8 %t74, ptr %a25
  br label %join28
join28:
  %t75 = load i8, ptr %a25
  ret void
}

; rt_step  graph:9b8343baf5a89c53
define internal void @ax_rt_step__seq(ptr %p_state, i64 %p_events, ptr %p_handler) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  %a3 = alloca ptr
  %a8 = alloca i1
  %a16 = alloca i8
  %a25 = alloca i1
  %a33 = alloca i8
  %a39 = alloca i8
  %a44 = alloca i8
  %a52 = alloca i1
  %a60 = alloca i8
  %a67 = alloca i8
  %a72 = alloca i8
  %a80 = alloca i1
  %a86 = alloca i1
  %a95 = alloca i8
  %a102 = alloca i64
  %a114 = alloca i64
  %a117 = alloca i8
  %a126 = alloca i8
  %a131 = alloca i8
  %a137 = alloca i8
  %a146 = alloca i8
  %a151 = alloca i1
  %a159 = alloca i8
  store ptr %p_state, ptr %a1
  store i64 %p_events, ptr %a2
  store ptr %p_handler, ptr %a3
  %t4 = load i64, ptr %a2
  %t5 = sdiv i64 %t4, 8
  %t6 = srem i64 %t5, 2
  %t7 = icmp eq i64 %t6, 1
  store i1 %t7, ptr %a8
  br i1 %t7, label %join10, label %rhs9
rhs9:
  %t11 = load i64, ptr %a2
  %t12 = sdiv i64 %t11, 32
  %t13 = srem i64 %t12, 2
  %t14 = icmp eq i64 %t13, 1
  store i1 %t14, ptr %a8
  br label %join10
join10:
  %t15 = load i1, ptr %a8
  br i1 %t15, label %then17, label %else18
then17:
  %t20 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t20)
  store i8 0, ptr %a16
  br label %join19
else18:
  %t21 = load ptr, ptr %a1
  %t22 = getelementptr i8, ptr %t21, i64 32
  %t23 = load i64, ptr %t22, align 1
  %t24 = icmp sgt i64 %t23, 0
  store i1 %t24, ptr %a25
  br i1 %t24, label %rhs26, label %join27
rhs26:
  %t28 = load i64, ptr %a2
  %t29 = sdiv i64 %t28, 4
  %t30 = srem i64 %t29, 2
  %t31 = icmp eq i64 %t30, 1
  store i1 %t31, ptr %a25
  br label %join27
join27:
  %t32 = load i1, ptr %a25
  br i1 %t32, label %then34, label %else35
then34:
  %t37 = load ptr, ptr %a1
  call void @ax_rt_flush__seq(ptr %t37)
  store i8 0, ptr %a33
  br label %join36
else35:
  store i8 0, ptr %a33
  br label %join36
join36:
  %t38 = load i8, ptr %a33
  store i8 %t38, ptr %a39
  %t40 = load ptr, ptr %a1
  %t41 = getelementptr i8, ptr %t40, i64 0
  %t42 = load i64, ptr %t41, align 1
  %t43 = icmp slt i64 %t42, 0
  br i1 %t43, label %then45, label %else46
then45:
  store i8 0, ptr %a44
  br label %join47
else46:
  %t48 = load ptr, ptr %a1
  %t49 = getelementptr i8, ptr %t48, i64 32
  %t50 = load i64, ptr %t49, align 1
  %t51 = icmp eq i64 %t50, 0
  store i1 %t51, ptr %a52
  br i1 %t51, label %rhs53, label %join54
rhs53:
  %t55 = load ptr, ptr %a1
  %t56 = getelementptr i8, ptr %t55, i64 16
  %t57 = load i64, ptr %t56, align 1
  %t58 = icmp sgt i64 %t57, 0
  store i1 %t58, ptr %a52
  br label %join54
join54:
  %t59 = load i1, ptr %a52
  br i1 %t59, label %then61, label %else62
then61:
  %t64 = load ptr, ptr %a1
  %t65 = load ptr, ptr %a3
  call void @ax_rt_prepare__seq(ptr %t64, ptr %t65)
  store i8 0, ptr %a60
  br label %join63
else62:
  store i8 0, ptr %a60
  br label %join63
join63:
  %t66 = load i8, ptr %a60
  store i8 %t66, ptr %a67
  %t68 = load ptr, ptr %a1
  %t69 = getelementptr i8, ptr %t68, i64 0
  %t70 = load i64, ptr %t69, align 1
  %t71 = icmp slt i64 %t70, 0
  br i1 %t71, label %then73, label %else74
then73:
  store i8 0, ptr %a72
  br label %join75
else74:
  %t76 = load ptr, ptr %a1
  %t77 = getelementptr i8, ptr %t76, i64 32
  %t78 = load i64, ptr %t77, align 1
  %t79 = icmp eq i64 %t78, 0
  store i1 %t79, ptr %a80
  br i1 %t79, label %rhs81, label %join82
rhs81:
  %t83 = load i64, ptr %a2
  %t84 = srem i64 %t83, 2
  %t85 = icmp eq i64 %t84, 1
  store i1 %t85, ptr %a86
  br i1 %t85, label %join88, label %rhs87
rhs87:
  %t89 = load i64, ptr %a2
  %t90 = sdiv i64 %t89, 16
  %t91 = srem i64 %t90, 2
  %t92 = icmp eq i64 %t91, 1
  store i1 %t92, ptr %a86
  br label %join88
join88:
  %t93 = load i1, ptr %a86
  store i1 %t93, ptr %a80
  br label %join82
join82:
  %t94 = load i1, ptr %a80
  br i1 %t94, label %then96, label %else97
then96:
  %t99 = load ptr, ptr %a1
  %t100 = getelementptr i8, ptr %t99, i64 16
  %t101 = load i64, ptr %t100, align 1
  store i64 %t101, ptr %a102
  %t103 = load ptr, ptr %a1
  %t104 = getelementptr i8, ptr %t103, i64 0
  %t105 = load i64, ptr %t104, align 1
  %t106 = load ptr, ptr %a1
  %t107 = getelementptr i8, ptr %t106, i64 8
  %t108 = load ptr, ptr %t107, align 1
  %t109 = load i64, ptr %a102
  %t110 = getelementptr i8, ptr %t108, i64 %t109
  %t111 = load i64, ptr %a102
  %t112 = sub i64 65536, %t111
  %t113 = call i64 @ax_rt_read__seq(i64 %t105, ptr %t110, i64 %t112)
  store i64 %t113, ptr %a114
  %t115 = load i64, ptr %a114
  %t116 = icmp sgt i64 %t115, 0
  br i1 %t116, label %then118, label %else119
then118:
  %t121 = load ptr, ptr %a1
  %t122 = load i64, ptr %a102
  %t123 = load i64, ptr %a114
  %t124 = add i64 %t122, %t123
  %t125 = getelementptr i8, ptr %t121, i64 16
  store i64 %t124, ptr %t125, align 1
  store i8 0, ptr %a126
  %t127 = load ptr, ptr %a1
  %t128 = load ptr, ptr %a3
  call void @ax_rt_prepare__seq(ptr %t127, ptr %t128)
  store i8 0, ptr %a117
  br label %join120
else119:
  %t129 = load i64, ptr %a114
  %t130 = icmp eq i64 %t129, 0
  br i1 %t130, label %then132, label %else133
then132:
  %t135 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t135)
  store i8 0, ptr %a131
  br label %join134
else133:
  %t136 = call i1 @ax_rt_retry__seq()
  br i1 %t136, label %then138, label %else139
then138:
  store i8 0, ptr %a137
  br label %join140
else139:
  %t141 = load ptr, ptr %a1
  call void @ax_rt_drop__seq(ptr %t141)
  store i8 0, ptr %a137
  br label %join140
join140:
  %t142 = load i8, ptr %a137
  store i8 %t142, ptr %a131
  br label %join134
join134:
  %t143 = load i8, ptr %a131
  store i8 %t143, ptr %a117
  br label %join120
join120:
  %t144 = load i8, ptr %a117
  store i8 %t144, ptr %a95
  br label %join98
else97:
  store i8 0, ptr %a95
  br label %join98
join98:
  %t145 = load i8, ptr %a95
  store i8 %t145, ptr %a146
  %t147 = load ptr, ptr %a1
  %t148 = getelementptr i8, ptr %t147, i64 0
  %t149 = load i64, ptr %t148, align 1
  %t150 = icmp sge i64 %t149, 0
  store i1 %t150, ptr %a151
  br i1 %t150, label %rhs152, label %join153
rhs152:
  %t154 = load ptr, ptr %a1
  %t155 = getelementptr i8, ptr %t154, i64 32
  %t156 = load i64, ptr %t155, align 1
  %t157 = icmp sgt i64 %t156, 0
  store i1 %t157, ptr %a151
  br label %join153
join153:
  %t158 = load i1, ptr %a151
  br i1 %t158, label %then160, label %else161
then160:
  %t163 = load ptr, ptr %a1
  call void @ax_rt_flush__seq(ptr %t163)
  store i8 0, ptr %a159
  br label %join162
else161:
  store i8 0, ptr %a159
  br label %join162
join162:
  %t164 = load i8, ptr %a159
  store i8 %t164, ptr %a72
  br label %join75
join75:
  %t165 = load i8, ptr %a72
  store i8 %t165, ptr %a44
  br label %join47
join47:
  %t166 = load i8, ptr %a44
  store i8 %t166, ptr %a16
  br label %join19
join19:
  %t167 = load i8, ptr %a16
  ret void
}

; rt_accept  graph:98195813abcab27b
define internal void @ax_rt_accept__seq(i64 %p_listener, ptr %p_states, ptr %p_local, ptr %p_control, i64 %p_worker, i64 %p_workers) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca ptr
  %a5 = alloca i64
  %a6 = alloca i64
  %a12 = alloca i8
  %a18 = alloca i64
  %a21 = alloca i8
  %a28 = alloca i64
  %a31 = alloca i1
  %a38 = alloca i8
  %a44 = alloca i64
  %a49 = alloca ptr
  %a53 = alloca ptr
  %a55 = alloca ptr
  %a59 = alloca i8
  %a63 = alloca i64
  %a67 = alloca i8
  %a71 = alloca i8
  %a75 = alloca i8
  %a81 = alloca i8
  %a86 = alloca i64
  %a90 = alloca i8
  %a93 = alloca i8
  %a98 = alloca ptr
  %a102 = alloca i8
  %a111 = alloca i64
  %a113 = alloca i8
  store i64 %p_listener, ptr %a1
  store ptr %p_states, ptr %a2
  store ptr %p_local, ptr %a3
  store ptr %p_control, ptr %a4
  store i64 %p_worker, ptr %a5
  store i64 %p_workers, ptr %a6
  %t7 = load ptr, ptr %a4
  %t8 = getelementptr i8, ptr %t7, i64 0
  %t9 = load i64, ptr %t8, align 1
  %t10 = load i64, ptr %a5
  %t11 = icmp ne i64 %t9, %t10
  br i1 %t11, label %then13, label %else14
then13:
  store i8 0, ptr %a12
  br label %join15
else14:
  %t16 = load i64, ptr %a1
  %t17 = call i64 @ax_rt_accept_fd__seq(i64 %t16)
  store i64 %t17, ptr %a18
  %t19 = load i64, ptr %a18
  %t20 = icmp slt i64 %t19, 0
  br i1 %t20, label %then22, label %else23
then22:
  store i8 0, ptr %a21
  br label %join24
else23:
  %t25 = load ptr, ptr %a3
  %t26 = getelementptr i8, ptr %t25, i64 0
  %t27 = load i64, ptr %t26, align 1
  store i64 %t27, ptr %a28
  %t29 = load i64, ptr %a28
  %t30 = icmp eq i64 %t29, 1024
  store i1 %t30, ptr %a31
  br i1 %t30, label %join33, label %rhs32
rhs32:
  %t34 = load i64, ptr %a18
  %t35 = call i64 @ax_rt_nonblock__seq(i64 %t34)
  %t36 = icmp slt i64 %t35, 0
  store i1 %t36, ptr %a31
  br label %join33
join33:
  %t37 = load i1, ptr %a31
  br i1 %t37, label %then39, label %else40
then39:
  %t42 = load i64, ptr %a18
  %t43 = call i64 @ax_rt_close__seq(i64 %t42)
  store i64 %t43, ptr %a44
  store i8 0, ptr %a38
  br label %join41
else40:
  %t45 = load ptr, ptr %a2
  %t46 = load i64, ptr %a28
  %t47 = mul i64 %t46, 64
  %t48 = getelementptr i8, ptr %t45, i64 %t47
  store ptr %t48, ptr %a49
  %t50 = load ptr, ptr %a49
  %t51 = trunc i64 0 to i32
  %t52 = call ptr @memset(ptr %t50, i32 %t51, i64 64)
  store ptr %t52, ptr %a53
  %t54 = alloca i8, i64 8, align 16
  store ptr %t54, ptr %a55
  %t56 = load ptr, ptr %a55
  %t57 = trunc i64 1 to i32
  %t58 = getelementptr i8, ptr %t56, i64 0
  store i32 %t57, ptr %t58, align 1
  store i8 0, ptr %a59
  %t60 = load i64, ptr %a18
  %t61 = load ptr, ptr %a55
  %t62 = call i64 @ax_rt_setsockopt__seq(i64 %t60, i64 6, i64 1, ptr %t61, i64 4)
  store i64 %t62, ptr %a63
  %t64 = load ptr, ptr %a49
  %t65 = call ptr @ax_alloc(i64 65536)
  %t66 = getelementptr i8, ptr %t64, i64 8
  store ptr %t65, ptr %t66, align 1
  store i8 0, ptr %a67
  %t68 = load ptr, ptr %a49
  %t69 = call ptr @ax_alloc(i64 4096)
  %t70 = getelementptr i8, ptr %t68, i64 24
  store ptr %t69, ptr %t70, align 1
  store i8 0, ptr %a71
  %t72 = load ptr, ptr %a49
  %t73 = load i64, ptr %a18
  %t74 = getelementptr i8, ptr %t72, i64 0
  store i64 %t73, ptr %t74, align 1
  store i8 0, ptr %a75
  %t76 = load ptr, ptr %a3
  %t77 = load i64, ptr %a28
  %t78 = add i64 %t77, 1
  %t79 = getelementptr i8, ptr %t76, i64 0
  store i64 %t78, ptr %t79, align 1
  store i8 0, ptr %a38
  br label %join41
join41:
  %t80 = load i8, ptr %a38
  store i8 %t80, ptr %a81
  %t82 = load i64, ptr %a5
  %t83 = add i64 %t82, 1
  %t84 = load i64, ptr %a6
  %t85 = srem i64 %t83, %t84
  store i64 %t85, ptr %a86
  %t87 = load ptr, ptr %a4
  %t88 = load i64, ptr %a86
  %t89 = getelementptr i8, ptr %t87, i64 0
  store i64 %t88, ptr %t89, align 1
  store i8 0, ptr %a90
  %t91 = load i64, ptr %a6
  %t92 = icmp sgt i64 %t91, 1
  br i1 %t92, label %then94, label %else95
then94:
  %t97 = alloca i8, i64 8, align 16
  store ptr %t97, ptr %a98
  %t99 = load ptr, ptr %a98
  %t100 = trunc i64 1 to i8
  %t101 = getelementptr i8, ptr %t99, i64 0
  store i8 %t100, ptr %t101, align 1
  store i8 0, ptr %a102
  %t103 = load ptr, ptr %a4
  %t104 = load i64, ptr %a86
  %t105 = mul i64 %t104, 16
  %t106 = add i64 264, %t105
  %t107 = getelementptr i8, ptr %t103, i64 %t106
  %t108 = load i64, ptr %t107, align 1
  %t109 = load ptr, ptr %a98
  %t110 = call i64 @ax_rt_write__seq(i64 %t108, ptr %t109, i64 1)
  store i64 %t110, ptr %a111
  store i8 0, ptr %a93
  br label %join96
else95:
  store i8 0, ptr %a93
  br label %join96
join96:
  %t112 = load i8, ptr %a93
  store i8 %t112, ptr %a113
  store i8 0, ptr %a21
  br label %join24
join24:
  %t114 = load i8, ptr %a21
  store i8 %t114, ptr %a12
  br label %join15
join15:
  %t115 = load i8, ptr %a12
  ret void
}

; rt_compact  graph:751e00848e8b9703
define internal i64 @ax_rt_compact__seq(ptr %p_states, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca i64
  %a3 = alloca i64
  %a4 = alloca i64
  %a19 = alloca i64
  %a27 = alloca i8
  %a40 = alloca ptr
  %a42 = alloca i8
  store ptr %p_states, ptr %a1
  store i64 %p_n, ptr %a2
  store i64 0, ptr %a3
  store i64 0, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load i64, ptr %a3
  %t9 = load i64, ptr %a2
  %t10 = icmp slt i64 %t8, %t9
  br i1 %t10, label %loop_body6, label %loop_exit7
loop_body6:
  %t11 = load i64, ptr %a3
  %t12 = add i64 %t11, 1
  %t13 = load ptr, ptr %a1
  %t14 = load i64, ptr %a3
  %t15 = mul i64 %t14, 64
  %t16 = getelementptr i8, ptr %t13, i64 %t15
  %t17 = load i64, ptr %t16, align 1
  %t18 = icmp slt i64 %t17, 0
  br i1 %t18, label %then20, label %else21
then20:
  %t23 = load i64, ptr %a4
  store i64 %t23, ptr %a19
  br label %join22
else21:
  %t24 = load i64, ptr %a3
  %t25 = load i64, ptr %a4
  %t26 = icmp ne i64 %t24, %t25
  br i1 %t26, label %then28, label %else29
then28:
  %t31 = load ptr, ptr %a1
  %t32 = load i64, ptr %a4
  %t33 = mul i64 %t32, 64
  %t34 = getelementptr i8, ptr %t31, i64 %t33
  %t35 = load ptr, ptr %a1
  %t36 = load i64, ptr %a3
  %t37 = mul i64 %t36, 64
  %t38 = getelementptr i8, ptr %t35, i64 %t37
  %t39 = call ptr @memcpy(ptr %t34, ptr %t38, i64 64)
  store ptr %t39, ptr %a40
  store i8 0, ptr %a27
  br label %join30
else29:
  store i8 0, ptr %a27
  br label %join30
join30:
  %t41 = load i8, ptr %a27
  store i8 %t41, ptr %a42
  %t43 = load i64, ptr %a4
  %t44 = add i64 %t43, 1
  store i64 %t44, ptr %a19
  br label %join22
join22:
  %t45 = load i64, ptr %a19
  store i64 %t12, ptr %a3
  store i64 %t45, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t46 = load i64, ptr %a4
  ret i64 %t46
}

; rt_events  graph:10cbacbecd86a4de
define internal void @ax_rt_events__seq(ptr %p_polls, ptr %p_states, i64 %p_n, i64 %p_listener, ptr %p_control, i64 %p_worker) "no-builtins" {
entry:
  %a1 = alloca ptr
  %a2 = alloca ptr
  %a3 = alloca i64
  %a4 = alloca i64
  %a5 = alloca ptr
  %a6 = alloca i64
  %a13 = alloca i64
  %a21 = alloca i8
  %a25 = alloca i8
  %a35 = alloca i8
  %a39 = alloca i8
  %a40 = alloca i64
  %a51 = alloca ptr
  %a61 = alloca i8
  %a71 = alloca i1
  %a79 = alloca i64
  %a86 = alloca i8
  %a90 = alloca i64
  store ptr %p_polls, ptr %a1
  store ptr %p_states, ptr %a2
  store i64 %p_n, ptr %a3
  store i64 %p_listener, ptr %a4
  store ptr %p_control, ptr %a5
  store i64 %p_worker, ptr %a6
  %t7 = load ptr, ptr %a1
  %t8 = load ptr, ptr %a5
  %t9 = getelementptr i8, ptr %t8, i64 0
  %t10 = load i64, ptr %t9, align 1
  %t11 = load i64, ptr %a6
  %t12 = icmp eq i64 %t10, %t11
  br i1 %t12, label %then14, label %else15
then14:
  %t17 = load i64, ptr %a4
  store i64 %t17, ptr %a13
  br label %join16
else15:
  store i64 -1, ptr %a13
  br label %join16
join16:
  %t18 = load i64, ptr %a13
  %t19 = trunc i64 %t18 to i32
  %t20 = getelementptr i8, ptr %t7, i64 0
  store i32 %t19, ptr %t20, align 1
  store i8 0, ptr %a21
  %t22 = load ptr, ptr %a1
  %t23 = trunc i64 1 to i32
  %t24 = getelementptr i8, ptr %t22, i64 4
  store i32 %t23, ptr %t24, align 1
  store i8 0, ptr %a25
  %t26 = load ptr, ptr %a1
  %t27 = load ptr, ptr %a5
  %t28 = load i64, ptr %a6
  %t29 = mul i64 %t28, 16
  %t30 = add i64 256, %t29
  %t31 = getelementptr i8, ptr %t27, i64 %t30
  %t32 = load i64, ptr %t31, align 1
  %t33 = trunc i64 %t32 to i32
  %t34 = getelementptr i8, ptr %t26, i64 8
  store i32 %t33, ptr %t34, align 1
  store i8 0, ptr %a35
  %t36 = load ptr, ptr %a1
  %t37 = trunc i64 1 to i32
  %t38 = getelementptr i8, ptr %t36, i64 12
  store i32 %t37, ptr %t38, align 1
  store i8 0, ptr %a39
  store i64 0, ptr %a40
  br label %loop_cond41
loop_cond41:
  %t44 = load i64, ptr %a40
  %t45 = load i64, ptr %a3
  %t46 = icmp slt i64 %t44, %t45
  br i1 %t46, label %loop_body42, label %loop_exit43
loop_body42:
  %t47 = load ptr, ptr %a2
  %t48 = load i64, ptr %a40
  %t49 = mul i64 %t48, 64
  %t50 = getelementptr i8, ptr %t47, i64 %t49
  store ptr %t50, ptr %a51
  %t52 = load ptr, ptr %a1
  %t53 = load i64, ptr %a40
  %t54 = add i64 %t53, 2
  %t55 = mul i64 %t54, 8
  %t56 = load ptr, ptr %a51
  %t57 = getelementptr i8, ptr %t56, i64 0
  %t58 = load i64, ptr %t57, align 1
  %t59 = trunc i64 %t58 to i32
  %t60 = getelementptr i8, ptr %t52, i64 %t55
  store i32 %t59, ptr %t60, align 1
  store i8 0, ptr %a61
  %t62 = load ptr, ptr %a1
  %t63 = load i64, ptr %a40
  %t64 = add i64 %t63, 2
  %t65 = mul i64 %t64, 8
  %t66 = add i64 %t65, 4
  %t67 = load ptr, ptr %a51
  %t68 = getelementptr i8, ptr %t67, i64 32
  %t69 = load i64, ptr %t68, align 1
  %t70 = icmp sgt i64 %t69, 0
  store i1 %t70, ptr %a71
  br i1 %t70, label %join73, label %rhs72
rhs72:
  %t74 = load ptr, ptr %a51
  %t75 = getelementptr i8, ptr %t74, i64 56
  %t76 = load i64, ptr %t75, align 1
  %t77 = icmp eq i64 %t76, 1
  store i1 %t77, ptr %a71
  br label %join73
join73:
  %t78 = load i1, ptr %a71
  br i1 %t78, label %then80, label %else81
then80:
  store i64 4, ptr %a79
  br label %join82
else81:
  store i64 1, ptr %a79
  br label %join82
join82:
  %t83 = load i64, ptr %a79
  %t84 = trunc i64 %t83 to i32
  %t85 = getelementptr i8, ptr %t62, i64 %t66
  store i32 %t84, ptr %t85, align 1
  store i8 0, ptr %a86
  %t87 = load i64, ptr %a40
  %t88 = add i64 %t87, 1
  store i64 %t88, ptr %a40
  br label %loop_cond41
loop_exit43:
  %t89 = load i64, ptr %a40
  store i64 %t89, ptr %a90
  ret void
}

; rt_http_worker  graph:119bcdf3b081fa45
define internal i64 @ax_rt_http_worker__seq(i64 %p_listener, ptr %p_handler, ptr %p_control, i64 %p_worker, i64 %p_workers, i64 %p_parent) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca i64
  %a6 = alloca i64
  %a9 = alloca ptr
  %a11 = alloca ptr
  %a14 = alloca i8
  %a17 = alloca ptr
  %a19 = alloca ptr
  %a20 = alloca i1
  %a27 = alloca i1
  %a34 = alloca i8
  %a39 = alloca i8
  %a45 = alloca i64
  %a49 = alloca i8
  %a56 = alloca i8
  %a61 = alloca i64
  %a64 = alloca i1
  %a73 = alloca i1
  %a81 = alloca i8
  %a89 = alloca i8
  %a101 = alloca i64
  %a103 = alloca i8
  %a110 = alloca i8
  %a121 = alloca i8
  %a122 = alloca i64
  %a133 = alloca ptr
  %a142 = alloca i64
  %a147 = alloca i1
  %a153 = alloca i8
  %a161 = alloca i8
  %a165 = alloca i64
  store i64 %p_listener, ptr %a1
  store ptr %p_handler, ptr %a2
  store ptr %p_control, ptr %a3
  store i64 %p_worker, ptr %a4
  store i64 %p_workers, ptr %a5
  store i64 %p_parent, ptr %a6
  %t7 = mul i64 1024, 64
  %t8 = call ptr @ax_alloc(i64 %t7)
  store ptr %t8, ptr %a9
  %t10 = alloca i8, i64 16, align 16
  store ptr %t10, ptr %a11
  %t12 = load ptr, ptr %a11
  %t13 = getelementptr i8, ptr %t12, i64 0
  store i64 0, ptr %t13, align 1
  store i8 0, ptr %a14
  %t15 = mul i64 1026, 8
  %t16 = call ptr @ax_alloc(i64 %t15)
  store ptr %t16, ptr %a17
  %t18 = alloca i8, i64 64, align 16
  store ptr %t18, ptr %a19
  store i1 true, ptr %a20
  br label %loop_cond21
loop_cond21:
  %t24 = load i1, ptr %a20
  br i1 %t24, label %loop_body22, label %loop_exit23
loop_body22:
  %t25 = load i64, ptr %a4
  %t26 = icmp ne i64 %t25, 0
  store i1 %t26, ptr %a27
  br i1 %t26, label %rhs28, label %join29
rhs28:
  %t30 = call i64 @ax_rt_getppid__seq()
  %t31 = load i64, ptr %a6
  %t32 = icmp ne i64 %t30, %t31
  store i1 %t32, ptr %a27
  br label %join29
join29:
  %t33 = load i1, ptr %a27
  br i1 %t33, label %then35, label %else36
then35:
  call void @ax_exit(i64 0)
  store i8 0, ptr %a34
  br label %join37
else36:
  store i8 0, ptr %a34
  br label %join37
join37:
  %t38 = load i8, ptr %a34
  store i8 %t38, ptr %a39
  %t40 = load ptr, ptr %a9
  %t41 = load ptr, ptr %a11
  %t42 = getelementptr i8, ptr %t41, i64 0
  %t43 = load i64, ptr %t42, align 1
  %t44 = call i64 @ax_rt_compact__seq(ptr %t40, i64 %t43)
  store i64 %t44, ptr %a45
  %t46 = load ptr, ptr %a11
  %t47 = load i64, ptr %a45
  %t48 = getelementptr i8, ptr %t46, i64 0
  store i64 %t47, ptr %t48, align 1
  store i8 0, ptr %a49
  %t50 = load ptr, ptr %a17
  %t51 = load ptr, ptr %a9
  %t52 = load i64, ptr %a45
  %t53 = load i64, ptr %a1
  %t54 = load ptr, ptr %a3
  %t55 = load i64, ptr %a4
  call void @ax_rt_events__seq(ptr %t50, ptr %t51, i64 %t52, i64 %t53, ptr %t54, i64 %t55)
  store i8 0, ptr %a56
  %t57 = load ptr, ptr %a17
  %t58 = load i64, ptr %a45
  %t59 = add i64 %t58, 2
  %t60 = call i64 @ax_rt_poll__seq(ptr %t57, i64 %t59)
  store i64 %t60, ptr %a61
  %t62 = load i64, ptr %a61
  %t63 = icmp slt i64 %t62, 0
  br i1 %t63, label %then65, label %else66
then65:
  %t68 = call ptr @ax_rt_errno__seq()
  %t69 = getelementptr i8, ptr %t68, i64 0
  %t70 = load i32, ptr %t69, align 1
  %t71 = trunc i64 4 to i32
  %t72 = icmp eq i32 %t70, %t71
  br i1 %t72, label %then74, label %else75
then74:
  store i1 true, ptr %a73
  br label %join76
else75:
  %t77 = insertvalue %ax_arr undef, ptr @.bytes.27, 0
  %t78 = insertvalue %ax_arr %t77, i64 20, 1
  %t79 = insertvalue %ax_arr %t78, i64 0, 2
  %t80 = extractvalue %ax_arr %t79, 0
  call void @ax_trap(ptr %t80)
  store i8 0, ptr %a81
  store i1 false, ptr %a73
  br label %join76
join76:
  %t82 = load i1, ptr %a73
  store i1 %t82, ptr %a64
  br label %join67
else66:
  %t83 = load ptr, ptr %a17
  %t84 = getelementptr i8, ptr %t83, i64 14
  %t85 = load i8, ptr %t84, align 1
  %t86 = zext i8 %t85 to i64
  %t87 = srem i64 %t86, 2
  %t88 = icmp eq i64 %t87, 1
  br i1 %t88, label %then90, label %else91
then90:
  %t93 = load ptr, ptr %a3
  %t94 = load i64, ptr %a4
  %t95 = mul i64 %t94, 16
  %t96 = add i64 256, %t95
  %t97 = getelementptr i8, ptr %t93, i64 %t96
  %t98 = load i64, ptr %t97, align 1
  %t99 = load ptr, ptr %a19
  %t100 = call i64 @ax_rt_read__seq(i64 %t98, ptr %t99, i64 64)
  store i64 %t100, ptr %a101
  store i8 0, ptr %a89
  br label %join92
else91:
  store i8 0, ptr %a89
  br label %join92
join92:
  %t102 = load i8, ptr %a89
  store i8 %t102, ptr %a103
  %t104 = load ptr, ptr %a17
  %t105 = getelementptr i8, ptr %t104, i64 6
  %t106 = load i8, ptr %t105, align 1
  %t107 = zext i8 %t106 to i64
  %t108 = srem i64 %t107, 2
  %t109 = icmp eq i64 %t108, 1
  br i1 %t109, label %then111, label %else112
then111:
  %t114 = load i64, ptr %a1
  %t115 = load ptr, ptr %a9
  %t116 = load ptr, ptr %a11
  %t117 = load ptr, ptr %a3
  %t118 = load i64, ptr %a4
  %t119 = load i64, ptr %a5
  call void @ax_rt_accept__seq(i64 %t114, ptr %t115, ptr %t116, ptr %t117, i64 %t118, i64 %t119)
  store i8 0, ptr %a110
  br label %join113
else112:
  store i8 0, ptr %a110
  br label %join113
join113:
  %t120 = load i8, ptr %a110
  store i8 %t120, ptr %a121
  store i64 0, ptr %a122
  br label %loop_cond123
loop_cond123:
  %t126 = load i64, ptr %a122
  %t127 = load i64, ptr %a45
  %t128 = icmp slt i64 %t126, %t127
  br i1 %t128, label %loop_body124, label %loop_exit125
loop_body124:
  %t129 = load ptr, ptr %a9
  %t130 = load i64, ptr %a122
  %t131 = mul i64 %t130, 64
  %t132 = getelementptr i8, ptr %t129, i64 %t131
  store ptr %t132, ptr %a133
  %t134 = load ptr, ptr %a17
  %t135 = load i64, ptr %a122
  %t136 = add i64 %t135, 2
  %t137 = mul i64 %t136, 8
  %t138 = add i64 %t137, 6
  %t139 = getelementptr i8, ptr %t134, i64 %t138
  %t140 = load i8, ptr %t139, align 1
  %t141 = zext i8 %t140 to i64
  store i64 %t141, ptr %a142
  %t143 = load ptr, ptr %a133
  %t144 = getelementptr i8, ptr %t143, i64 0
  %t145 = load i64, ptr %t144, align 1
  %t146 = icmp sge i64 %t145, 0
  store i1 %t146, ptr %a147
  br i1 %t146, label %rhs148, label %join149
rhs148:
  %t150 = load i64, ptr %a142
  %t151 = icmp sgt i64 %t150, 0
  store i1 %t151, ptr %a147
  br label %join149
join149:
  %t152 = load i1, ptr %a147
  br i1 %t152, label %then154, label %else155
then154:
  %t157 = load ptr, ptr %a133
  %t158 = load i64, ptr %a142
  %t159 = load ptr, ptr %a2
  call void @ax_rt_step__seq(ptr %t157, i64 %t158, ptr %t159)
  store i8 0, ptr %a153
  br label %join156
else155:
  store i8 0, ptr %a153
  br label %join156
join156:
  %t160 = load i8, ptr %a153
  store i8 %t160, ptr %a161
  %t162 = load i64, ptr %a122
  %t163 = add i64 %t162, 1
  store i64 %t163, ptr %a122
  br label %loop_cond123
loop_exit125:
  %t164 = load i64, ptr %a122
  store i64 %t164, ptr %a165
  store i1 true, ptr %a64
  br label %join67
join67:
  %t166 = load i1, ptr %a64
  store i1 %t166, ptr %a20
  br label %loop_cond21
loop_exit23:
  ret i64 0
}

; ax_serve  graph:c332df94539322d6
define i64 @ax_serve(i64 %p_port, ptr %p_handler) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a5 = alloca i64
  %a7 = alloca i64
  %a9 = alloca i64
  %a11 = alloca ptr
  %a13 = alloca ptr
  %a14 = alloca i64
  %a23 = alloca i64
  %a26 = alloca i8
  %a35 = alloca i8
  %a40 = alloca i64
  %a45 = alloca i64
  %a52 = alloca i8
  %a59 = alloca i8
  %a62 = alloca i64
  %a65 = alloca i64
  %a69 = alloca i64
  %a70 = alloca i64
  %a71 = alloca i64
  %a77 = alloca i1
  %a87 = alloca i64
  %a90 = alloca i64
  %a98 = alloca i8
  %a101 = alloca i64
  %a109 = alloca i64
  %a112 = alloca i8
  %a120 = alloca i8
  %a122 = alloca ptr
  %a126 = alloca i64
  %a129 = alloca i8
  %a136 = alloca i8
  store i64 %p_port, ptr %a1
  store ptr %p_handler, ptr %a2
  %t3 = load i64, ptr %a1
  %t4 = call i64 @ax_rt_listener__seq(i64 %t3)
  store i64 %t4, ptr %a5
  %t6 = call i64 @ax_rt_threads__seq()
  store i64 %t6, ptr %a7
  %t8 = call i64 @ax_rt_getpid__seq()
  store i64 %t8, ptr %a9
  %t10 = call ptr @ax_rt_map__seq(i64 65536)
  store ptr %t10, ptr %a11
  %t12 = alloca i8, i64 8, align 16
  store ptr %t12, ptr %a13
  store i64 0, ptr %a14
  br label %loop_cond15
loop_cond15:
  %t18 = load i64, ptr %a14
  %t19 = load i64, ptr %a7
  %t20 = icmp slt i64 %t18, %t19
  br i1 %t20, label %loop_body16, label %loop_exit17
loop_body16:
  %t21 = load ptr, ptr %a13
  %t22 = call i64 @ax_rt_socketpair__seq(ptr %t21)
  store i64 %t22, ptr %a23
  %t24 = load i64, ptr %a23
  %t25 = icmp slt i64 %t24, 0
  br i1 %t25, label %then27, label %else28
then27:
  %t30 = insertvalue %ax_arr undef, ptr @.bytes.28, 0
  %t31 = insertvalue %ax_arr %t30, i64 38, 1
  %t32 = insertvalue %ax_arr %t31, i64 0, 2
  %t33 = extractvalue %ax_arr %t32, 0
  call void @ax_trap(ptr %t33)
  store i8 0, ptr %a26
  br label %join29
else28:
  store i8 0, ptr %a26
  br label %join29
join29:
  %t34 = load i8, ptr %a26
  store i8 %t34, ptr %a35
  %t36 = load ptr, ptr %a13
  %t37 = getelementptr i8, ptr %t36, i64 0
  %t38 = load i32, ptr %t37, align 1
  %t39 = sext i32 %t38 to i64
  store i64 %t39, ptr %a40
  %t41 = load ptr, ptr %a13
  %t42 = getelementptr i8, ptr %t41, i64 4
  %t43 = load i32, ptr %t42, align 1
  %t44 = sext i32 %t43 to i64
  store i64 %t44, ptr %a45
  %t46 = load ptr, ptr %a11
  %t47 = load i64, ptr %a14
  %t48 = mul i64 %t47, 16
  %t49 = add i64 256, %t48
  %t50 = load i64, ptr %a40
  %t51 = getelementptr i8, ptr %t46, i64 %t49
  store i64 %t50, ptr %t51, align 1
  store i8 0, ptr %a52
  %t53 = load ptr, ptr %a11
  %t54 = load i64, ptr %a14
  %t55 = mul i64 %t54, 16
  %t56 = add i64 264, %t55
  %t57 = load i64, ptr %a45
  %t58 = getelementptr i8, ptr %t53, i64 %t56
  store i64 %t57, ptr %t58, align 1
  store i8 0, ptr %a59
  %t60 = load i64, ptr %a40
  %t61 = call i64 @ax_rt_nonblock__seq(i64 %t60)
  store i64 %t61, ptr %a62
  %t63 = load i64, ptr %a45
  %t64 = call i64 @ax_rt_nonblock__seq(i64 %t63)
  store i64 %t64, ptr %a65
  %t66 = load i64, ptr %a14
  %t67 = add i64 %t66, 1
  store i64 %t67, ptr %a14
  br label %loop_cond15
loop_exit17:
  %t68 = load i64, ptr %a14
  store i64 %t68, ptr %a69
  store i64 1, ptr %a70
  store i64 0, ptr %a71
  br label %loop_cond72
loop_cond72:
  %t75 = load i64, ptr %a71
  %t76 = icmp eq i64 %t75, 0
  store i1 %t76, ptr %a77
  br i1 %t76, label %rhs78, label %join79
rhs78:
  %t80 = load i64, ptr %a70
  %t81 = load i64, ptr %a7
  %t82 = icmp slt i64 %t80, %t81
  store i1 %t82, ptr %a77
  br label %join79
join79:
  %t83 = load i1, ptr %a77
  br i1 %t83, label %loop_body73, label %loop_exit74
loop_body73:
  %t84 = load i64, ptr %a70
  %t85 = add i64 %t84, 1
  %t86 = call i64 @ax_rt_fork__seq()
  store i64 %t86, ptr %a87
  %t88 = load i64, ptr %a87
  %t89 = icmp slt i64 %t88, 0
  br i1 %t89, label %then91, label %else92
then91:
  %t94 = insertvalue %ax_arr undef, ptr @.bytes.29, 0
  %t95 = insertvalue %ax_arr %t94, i64 24, 1
  %t96 = insertvalue %ax_arr %t95, i64 0, 2
  %t97 = extractvalue %ax_arr %t96, 0
  call void @ax_trap(ptr %t97)
  store i8 0, ptr %a98
  store i64 0, ptr %a90
  br label %join93
else92:
  %t99 = load i64, ptr %a87
  %t100 = icmp eq i64 %t99, 0
  br i1 %t100, label %then102, label %else103
then102:
  %t105 = load i64, ptr %a70
  store i64 %t105, ptr %a101
  br label %join104
else103:
  store i64 0, ptr %a101
  br label %join104
join104:
  %t106 = load i64, ptr %a101
  store i64 %t106, ptr %a90
  br label %join93
join93:
  %t107 = load i64, ptr %a90
  store i64 %t85, ptr %a70
  store i64 %t107, ptr %a71
  br label %loop_cond72
loop_exit74:
  %t108 = load i64, ptr %a71
  store i64 %t108, ptr %a109
  %t110 = load i64, ptr %a109
  %t111 = icmp eq i64 %t110, 0
  br i1 %t111, label %then113, label %else114
then113:
  %t116 = insertvalue %ax_arr undef, ptr @.bytes.30, 0
  %t117 = insertvalue %ax_arr %t116, i64 23, 1
  %t118 = insertvalue %ax_arr %t117, i64 0, 2
  %t119 = extractvalue %ax_arr %t118, 0
  call void @ax_rt_write_all__seq(i64 2, ptr %t119, i64 23)
  store i8 0, ptr %a120
  %t121 = alloca i8, i64 64, align 16
  store ptr %t121, ptr %a122
  %t123 = load ptr, ptr %a122
  %t124 = load i64, ptr %a7
  %t125 = call i64 @ax_rt_format_integer__seq(ptr %t123, i64 63, i64 %t124)
  store i64 %t125, ptr %a126
  %t127 = load ptr, ptr %a122
  %t128 = getelementptr i8, ptr %t127, i64 63
  store i8 10, ptr %t128, align 1
  store i8 0, ptr %a129
  %t130 = load ptr, ptr %a122
  %t131 = load i64, ptr %a126
  %t132 = getelementptr i8, ptr %t130, i64 %t131
  %t133 = load i64, ptr %a126
  %t134 = sub i64 64, %t133
  call void @ax_rt_write_all__seq(i64 2, ptr %t132, i64 %t134)
  store i8 0, ptr %a112
  br label %join115
else114:
  store i8 0, ptr %a112
  br label %join115
join115:
  %t135 = load i8, ptr %a112
  store i8 %t135, ptr %a136
  %t137 = load i64, ptr %a5
  %t138 = load ptr, ptr %a2
  %t139 = load ptr, ptr %a11
  %t140 = load i64, ptr %a109
  %t141 = load i64, ptr %a7
  %t142 = load i64, ptr %a9
  %t143 = call i64 @ax_rt_serve_worker__seq(i64 %t137, ptr %t138, ptr %t139, i64 %t140, i64 %t141, i64 %t142)
  ret i64 %t143
}

; rt_epoll_apply  graph:2c0b02fbc121a31a
define internal void @ax_rt_epoll_apply__seq(i64 %p_epfd, i64 %p_op, i64 %p_fd, i64 %p_mask, i64 %p_token) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i64
  %a12 = alloca i64
  %a15 = alloca i8
  store i64 %p_epfd, ptr %a1
  store i64 %p_op, ptr %a2
  store i64 %p_fd, ptr %a3
  store i64 %p_mask, ptr %a4
  store i64 %p_token, ptr %a5
  %t6 = load i64, ptr %a1
  %t7 = load i64, ptr %a2
  %t8 = load i64, ptr %a3
  %t9 = load i64, ptr %a4
  %t10 = load i64, ptr %a5
  %t11 = call i64 @ax_rt_epoll_ctl__seq(i64 %t6, i64 %t7, i64 %t8, i64 %t9, i64 %t10)
  store i64 %t11, ptr %a12
  %t13 = load i64, ptr %a12
  %t14 = icmp slt i64 %t13, 0
  br i1 %t14, label %then16, label %else17
then16:
  %t19 = insertvalue %ax_arr undef, ptr @.bytes.31, 0
  %t20 = insertvalue %ax_arr %t19, i64 25, 1
  %t21 = insertvalue %ax_arr %t20, i64 0, 2
  %t22 = extractvalue %ax_arr %t21, 0
  call void @ax_trap(ptr %t22)
  store i8 0, ptr %a15
  br label %join18
else17:
  store i8 0, ptr %a15
  br label %join18
join18:
  %t23 = load i8, ptr %a15
  ret void
}

; rt_epoll_sync  graph:785336366b37e508
define internal void @ax_rt_epoll_sync__seq(i64 %p_epfd, ptr %p_state, ptr %p_interests, i64 %p_index) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a9 = alloca i8
  %a17 = alloca i1
  %a25 = alloca i64
  %a30 = alloca i64
  %a38 = alloca i8
  %a49 = alloca i8
  store i64 %p_epfd, ptr %a1
  store ptr %p_state, ptr %a2
  store ptr %p_interests, ptr %a3
  store i64 %p_index, ptr %a4
  %t5 = load ptr, ptr %a2
  %t6 = getelementptr i8, ptr %t5, i64 0
  %t7 = load i64, ptr %t6, align 1
  %t8 = icmp slt i64 %t7, 0
  br i1 %t8, label %then10, label %else11
then10:
  store i8 0, ptr %a9
  br label %join12
else11:
  %t13 = load ptr, ptr %a2
  %t14 = getelementptr i8, ptr %t13, i64 32
  %t15 = load i64, ptr %t14, align 1
  %t16 = icmp sgt i64 %t15, 0
  store i1 %t16, ptr %a17
  br i1 %t16, label %join19, label %rhs18
rhs18:
  %t20 = load ptr, ptr %a2
  %t21 = getelementptr i8, ptr %t20, i64 56
  %t22 = load i64, ptr %t21, align 1
  %t23 = icmp eq i64 %t22, 1
  store i1 %t23, ptr %a17
  br label %join19
join19:
  %t24 = load i1, ptr %a17
  br i1 %t24, label %then26, label %else27
then26:
  store i64 4, ptr %a25
  br label %join28
else27:
  store i64 1, ptr %a25
  br label %join28
join28:
  %t29 = load i64, ptr %a25
  store i64 %t29, ptr %a30
  %t31 = load i64, ptr %a30
  %t32 = load ptr, ptr %a3
  %t33 = load i64, ptr %a4
  %t34 = mul i64 %t33, 8
  %t35 = getelementptr i8, ptr %t32, i64 %t34
  %t36 = load i64, ptr %t35, align 1
  %t37 = icmp eq i64 %t31, %t36
  br i1 %t37, label %then39, label %else40
then39:
  store i8 0, ptr %a38
  br label %join41
else40:
  %t42 = load i64, ptr %a1
  %t43 = load ptr, ptr %a2
  %t44 = getelementptr i8, ptr %t43, i64 0
  %t45 = load i64, ptr %t44, align 1
  %t46 = load i64, ptr %a30
  %t47 = load i64, ptr %a4
  %t48 = add i64 %t47, 2
  call void @ax_rt_epoll_apply__seq(i64 %t42, i64 3, i64 %t45, i64 %t46, i64 %t48)
  store i8 0, ptr %a49
  %t50 = load ptr, ptr %a3
  %t51 = load i64, ptr %a4
  %t52 = mul i64 %t51, 8
  %t53 = load i64, ptr %a30
  %t54 = getelementptr i8, ptr %t50, i64 %t52
  store i64 %t53, ptr %t54, align 1
  store i8 0, ptr %a38
  br label %join41
join41:
  %t55 = load i8, ptr %a38
  store i8 %t55, ptr %a9
  br label %join12
join12:
  %t56 = load i8, ptr %a9
  ret void
}

; rt_epoll_compact  graph:6725a65bcefab83f
define internal i64 @ax_rt_epoll_compact__seq(i64 %p_epfd, ptr %p_states, ptr %p_interests, i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca i64
  %a6 = alloca i64
  %a21 = alloca i64
  %a29 = alloca i8
  %a37 = alloca ptr
  %a44 = alloca ptr
  %a50 = alloca i64
  %a56 = alloca i8
  %a65 = alloca i8
  store i64 %p_epfd, ptr %a1
  store ptr %p_states, ptr %a2
  store ptr %p_interests, ptr %a3
  store i64 %p_n, ptr %a4
  store i64 0, ptr %a5
  store i64 0, ptr %a6
  br label %loop_cond7
loop_cond7:
  %t10 = load i64, ptr %a5
  %t11 = load i64, ptr %a4
  %t12 = icmp slt i64 %t10, %t11
  br i1 %t12, label %loop_body8, label %loop_exit9
loop_body8:
  %t13 = load i64, ptr %a5
  %t14 = add i64 %t13, 1
  %t15 = load ptr, ptr %a2
  %t16 = load i64, ptr %a5
  %t17 = mul i64 %t16, 64
  %t18 = getelementptr i8, ptr %t15, i64 %t17
  %t19 = load i64, ptr %t18, align 1
  %t20 = icmp slt i64 %t19, 0
  br i1 %t20, label %then22, label %else23
then22:
  %t25 = load i64, ptr %a6
  store i64 %t25, ptr %a21
  br label %join24
else23:
  %t26 = load i64, ptr %a5
  %t27 = load i64, ptr %a6
  %t28 = icmp eq i64 %t26, %t27
  br i1 %t28, label %then30, label %else31
then30:
  store i8 0, ptr %a29
  br label %join32
else31:
  %t33 = load ptr, ptr %a2
  %t34 = load i64, ptr %a5
  %t35 = mul i64 %t34, 64
  %t36 = getelementptr i8, ptr %t33, i64 %t35
  store ptr %t36, ptr %a37
  %t38 = load ptr, ptr %a2
  %t39 = load i64, ptr %a6
  %t40 = mul i64 %t39, 64
  %t41 = getelementptr i8, ptr %t38, i64 %t40
  %t42 = load ptr, ptr %a37
  %t43 = call ptr @memcpy(ptr %t41, ptr %t42, i64 64)
  store ptr %t43, ptr %a44
  %t45 = load ptr, ptr %a3
  %t46 = load i64, ptr %a5
  %t47 = mul i64 %t46, 8
  %t48 = getelementptr i8, ptr %t45, i64 %t47
  %t49 = load i64, ptr %t48, align 1
  store i64 %t49, ptr %a50
  %t51 = load ptr, ptr %a3
  %t52 = load i64, ptr %a6
  %t53 = mul i64 %t52, 8
  %t54 = load i64, ptr %a50
  %t55 = getelementptr i8, ptr %t51, i64 %t53
  store i64 %t54, ptr %t55, align 1
  store i8 0, ptr %a56
  %t57 = load i64, ptr %a1
  %t58 = load ptr, ptr %a37
  %t59 = getelementptr i8, ptr %t58, i64 0
  %t60 = load i64, ptr %t59, align 1
  %t61 = load i64, ptr %a50
  %t62 = load i64, ptr %a6
  %t63 = add i64 %t62, 2
  call void @ax_rt_epoll_apply__seq(i64 %t57, i64 3, i64 %t60, i64 %t61, i64 %t63)
  store i8 0, ptr %a29
  br label %join32
join32:
  %t64 = load i8, ptr %a29
  store i8 %t64, ptr %a65
  %t66 = load i64, ptr %a6
  %t67 = add i64 %t66, 1
  store i64 %t67, ptr %a21
  br label %join24
join24:
  %t68 = load i64, ptr %a21
  store i64 %t14, ptr %a5
  store i64 %t68, ptr %a6
  br label %loop_cond7
loop_exit9:
  %t69 = load i64, ptr %a6
  ret i64 %t69
}

; rt_epoll_listener  graph:49f1093cd8227eb8
define internal void @ax_rt_epoll_listener__seq(i64 %p_epfd, i64 %p_listener, ptr %p_control, i64 %p_worker, ptr %p_local) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca ptr
  %a11 = alloca i64
  %a16 = alloca i64
  %a22 = alloca i8
  %a29 = alloca i64
  %a35 = alloca i8
  store i64 %p_epfd, ptr %a1
  store i64 %p_listener, ptr %a2
  store ptr %p_control, ptr %a3
  store i64 %p_worker, ptr %a4
  store ptr %p_local, ptr %a5
  %t6 = load ptr, ptr %a3
  %t7 = getelementptr i8, ptr %t6, i64 0
  %t8 = load i64, ptr %t7, align 1
  %t9 = load i64, ptr %a4
  %t10 = icmp eq i64 %t8, %t9
  br i1 %t10, label %then12, label %else13
then12:
  store i64 1, ptr %a11
  br label %join14
else13:
  store i64 0, ptr %a11
  br label %join14
join14:
  %t15 = load i64, ptr %a11
  store i64 %t15, ptr %a16
  %t17 = load i64, ptr %a16
  %t18 = load ptr, ptr %a5
  %t19 = getelementptr i8, ptr %t18, i64 8
  %t20 = load i64, ptr %t19, align 1
  %t21 = icmp eq i64 %t17, %t20
  br i1 %t21, label %then23, label %else24
then23:
  store i8 0, ptr %a22
  br label %join25
else24:
  %t26 = load i64, ptr %a1
  %t27 = load i64, ptr %a16
  %t28 = icmp eq i64 %t27, 1
  br i1 %t28, label %then30, label %else31
then30:
  store i64 1, ptr %a29
  br label %join32
else31:
  store i64 2, ptr %a29
  br label %join32
join32:
  %t33 = load i64, ptr %a29
  %t34 = load i64, ptr %a2
  call void @ax_rt_epoll_apply__seq(i64 %t26, i64 %t33, i64 %t34, i64 1, i64 0)
  store i8 0, ptr %a35
  %t36 = load ptr, ptr %a5
  %t37 = load i64, ptr %a16
  %t38 = getelementptr i8, ptr %t36, i64 8
  store i64 %t37, ptr %t38, align 1
  store i8 0, ptr %a22
  br label %join25
join25:
  %t39 = load i8, ptr %a22
  ret void
}

; rt_epoll_accept  graph:29475284ef4ba4e3
define internal void @ax_rt_epoll_accept__seq(i64 %p_epfd, i64 %p_listener, ptr %p_states, ptr %p_interests, ptr %p_local, ptr %p_control, i64 %p_worker, i64 %p_workers) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a3 = alloca ptr
  %a4 = alloca ptr
  %a5 = alloca ptr
  %a6 = alloca ptr
  %a7 = alloca i64
  %a8 = alloca i64
  %a12 = alloca i64
  %a19 = alloca i8
  %a25 = alloca i8
  %a33 = alloca i8
  store i64 %p_epfd, ptr %a1
  store i64 %p_listener, ptr %a2
  store ptr %p_states, ptr %a3
  store ptr %p_interests, ptr %a4
  store ptr %p_local, ptr %a5
  store ptr %p_control, ptr %a6
  store i64 %p_worker, ptr %a7
  store i64 %p_workers, ptr %a8
  %t9 = load ptr, ptr %a5
  %t10 = getelementptr i8, ptr %t9, i64 0
  %t11 = load i64, ptr %t10, align 1
  store i64 %t11, ptr %a12
  %t13 = load i64, ptr %a2
  %t14 = load ptr, ptr %a3
  %t15 = load ptr, ptr %a5
  %t16 = load ptr, ptr %a6
  %t17 = load i64, ptr %a7
  %t18 = load i64, ptr %a8
  call void @ax_rt_accept__seq(i64 %t13, ptr %t14, ptr %t15, ptr %t16, i64 %t17, i64 %t18)
  store i8 0, ptr %a19
  %t20 = load i64, ptr %a12
  %t21 = load ptr, ptr %a5
  %t22 = getelementptr i8, ptr %t21, i64 0
  %t23 = load i64, ptr %t22, align 1
  %t24 = icmp eq i64 %t20, %t23
  br i1 %t24, label %then26, label %else27
then26:
  store i8 0, ptr %a25
  br label %join28
else27:
  %t29 = load ptr, ptr %a4
  %t30 = load i64, ptr %a12
  %t31 = mul i64 %t30, 8
  %t32 = getelementptr i8, ptr %t29, i64 %t31
  store i64 1, ptr %t32, align 1
  store i8 0, ptr %a33
  %t34 = load i64, ptr %a1
  %t35 = load ptr, ptr %a3
  %t36 = load i64, ptr %a12
  %t37 = mul i64 %t36, 64
  %t38 = getelementptr i8, ptr %t35, i64 %t37
  %t39 = load i64, ptr %t38, align 1
  %t40 = load i64, ptr %a12
  %t41 = add i64 %t40, 2
  call void @ax_rt_epoll_apply__seq(i64 %t34, i64 1, i64 %t39, i64 1, i64 %t41)
  store i8 0, ptr %a25
  br label %join28
join28:
  %t42 = load i8, ptr %a25
  ret void
}

; rt_http_epoll_worker  graph:b66d1a2952c610dc
define internal i64 @ax_rt_http_epoll_worker__seq(i64 %p_listener, ptr %p_handler, ptr %p_control, i64 %p_worker, i64 %p_workers, i64 %p_parent) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca i64
  %a6 = alloca i64
  %a8 = alloca i64
  %a11 = alloca i8
  %a20 = alloca i8
  %a23 = alloca ptr
  %a26 = alloca ptr
  %a29 = alloca ptr
  %a31 = alloca ptr
  %a35 = alloca ptr
  %a37 = alloca ptr
  %a45 = alloca i8
  %a46 = alloca i1
  %a53 = alloca i1
  %a60 = alloca i8
  %a65 = alloca i8
  %a71 = alloca i8
  %a75 = alloca i64
  %a78 = alloca i1
  %a87 = alloca i1
  %a95 = alloca i8
  %a99 = alloca i8
  %a102 = alloca i8
  %a106 = alloca i64
  %a107 = alloca i64
  %a120 = alloca i64
  %a127 = alloca i64
  %a130 = alloca i8
  %a138 = alloca i8
  %a150 = alloca i64
  %a153 = alloca i64
  %a156 = alloca i1
  %a163 = alloca i8
  %a175 = alloca ptr
  %a180 = alloca i8
  %a187 = alloca i8
  %a192 = alloca i8
  %a207 = alloca i8
  %a211 = alloca i64
  %a216 = alloca i8
  %a225 = alloca i64
  %a230 = alloca i8
  %a235 = alloca i8
  %a248 = alloca i8
  store i64 %p_listener, ptr %a1
  store ptr %p_handler, ptr %a2
  store ptr %p_control, ptr %a3
  store i64 %p_worker, ptr %a4
  store i64 %p_workers, ptr %a5
  store i64 %p_parent, ptr %a6
  %t7 = call i64 @ax_rt_epoll_create__seq()
  store i64 %t7, ptr %a8
  %t9 = load i64, ptr %a8
  %t10 = icmp slt i64 %t9, 0
  br i1 %t10, label %then12, label %else13
then12:
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.32, 0
  %t16 = insertvalue %ax_arr %t15, i64 29, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = extractvalue %ax_arr %t17, 0
  call void @ax_trap(ptr %t18)
  store i8 0, ptr %a11
  br label %join14
else13:
  store i8 0, ptr %a11
  br label %join14
join14:
  %t19 = load i8, ptr %a11
  store i8 %t19, ptr %a20
  %t21 = mul i64 1024, 64
  %t22 = call ptr @ax_alloc(i64 %t21)
  store ptr %t22, ptr %a23
  %t24 = mul i64 1024, 8
  %t25 = call ptr @ax_alloc(i64 %t24)
  store ptr %t25, ptr %a26
  %t27 = mul i64 1026, 16
  %t28 = call ptr @ax_alloc(i64 %t27)
  store ptr %t28, ptr %a29
  %t30 = alloca i8, i64 32, align 16
  store ptr %t30, ptr %a31
  %t32 = load ptr, ptr %a31
  %t33 = trunc i64 0 to i32
  %t34 = call ptr @memset(ptr %t32, i32 %t33, i64 32)
  store ptr %t34, ptr %a35
  %t36 = alloca i8, i64 64, align 16
  store ptr %t36, ptr %a37
  %t38 = load i64, ptr %a8
  %t39 = load ptr, ptr %a3
  %t40 = load i64, ptr %a4
  %t41 = mul i64 %t40, 16
  %t42 = add i64 256, %t41
  %t43 = getelementptr i8, ptr %t39, i64 %t42
  %t44 = load i64, ptr %t43, align 1
  call void @ax_rt_epoll_apply__seq(i64 %t38, i64 1, i64 %t44, i64 1, i64 1)
  store i8 0, ptr %a45
  store i1 true, ptr %a46
  br label %loop_cond47
loop_cond47:
  %t50 = load i1, ptr %a46
  br i1 %t50, label %loop_body48, label %loop_exit49
loop_body48:
  %t51 = load i64, ptr %a4
  %t52 = icmp ne i64 %t51, 0
  store i1 %t52, ptr %a53
  br i1 %t52, label %rhs54, label %join55
rhs54:
  %t56 = call i64 @ax_rt_getppid__seq()
  %t57 = load i64, ptr %a6
  %t58 = icmp ne i64 %t56, %t57
  store i1 %t58, ptr %a53
  br label %join55
join55:
  %t59 = load i1, ptr %a53
  br i1 %t59, label %then61, label %else62
then61:
  call void @ax_exit(i64 0)
  store i8 0, ptr %a60
  br label %join63
else62:
  store i8 0, ptr %a60
  br label %join63
join63:
  %t64 = load i8, ptr %a60
  store i8 %t64, ptr %a65
  %t66 = load i64, ptr %a8
  %t67 = load i64, ptr %a1
  %t68 = load ptr, ptr %a3
  %t69 = load i64, ptr %a4
  %t70 = load ptr, ptr %a31
  call void @ax_rt_epoll_listener__seq(i64 %t66, i64 %t67, ptr %t68, i64 %t69, ptr %t70)
  store i8 0, ptr %a71
  %t72 = load i64, ptr %a8
  %t73 = load ptr, ptr %a29
  %t74 = call i64 @ax_rt_epoll_wait__seq(i64 %t72, ptr %t73)
  store i64 %t74, ptr %a75
  %t76 = load i64, ptr %a75
  %t77 = icmp slt i64 %t76, 0
  br i1 %t77, label %then79, label %else80
then79:
  %t82 = call ptr @ax_rt_errno__seq()
  %t83 = getelementptr i8, ptr %t82, i64 0
  %t84 = load i32, ptr %t83, align 1
  %t85 = trunc i64 4 to i32
  %t86 = icmp eq i32 %t84, %t85
  br i1 %t86, label %then88, label %else89
then88:
  store i1 true, ptr %a87
  br label %join90
else89:
  %t91 = insertvalue %ax_arr undef, ptr @.bytes.33, 0
  %t92 = insertvalue %ax_arr %t91, i64 27, 1
  %t93 = insertvalue %ax_arr %t92, i64 0, 2
  %t94 = extractvalue %ax_arr %t93, 0
  call void @ax_trap(ptr %t94)
  store i8 0, ptr %a95
  store i1 false, ptr %a87
  br label %join90
join90:
  %t96 = load i1, ptr %a87
  store i1 %t96, ptr %a78
  br label %join81
else80:
  %t97 = load ptr, ptr %a31
  %t98 = getelementptr i8, ptr %t97, i64 16
  store i64 0, ptr %t98, align 1
  store i8 0, ptr %a99
  %t100 = load ptr, ptr %a31
  %t101 = getelementptr i8, ptr %t100, i64 24
  store i64 0, ptr %t101, align 1
  store i8 0, ptr %a102
  %t103 = load ptr, ptr %a31
  %t104 = getelementptr i8, ptr %t103, i64 0
  %t105 = load i64, ptr %t104, align 1
  store i64 %t105, ptr %a106
  store i64 0, ptr %a107
  br label %loop_cond108
loop_cond108:
  %t111 = load i64, ptr %a107
  %t112 = load i64, ptr %a75
  %t113 = icmp slt i64 %t111, %t112
  br i1 %t113, label %loop_body109, label %loop_exit110
loop_body109:
  %t114 = load ptr, ptr %a29
  %t115 = load i64, ptr %a107
  %t116 = mul i64 %t115, 16
  %t117 = add i64 %t116, 8
  %t118 = getelementptr i8, ptr %t114, i64 %t117
  %t119 = load i64, ptr %t118, align 1
  store i64 %t119, ptr %a120
  %t121 = load ptr, ptr %a29
  %t122 = load i64, ptr %a107
  %t123 = mul i64 %t122, 16
  %t124 = getelementptr i8, ptr %t121, i64 %t123
  %t125 = load i32, ptr %t124, align 1
  %t126 = sext i32 %t125 to i64
  store i64 %t126, ptr %a127
  %t128 = load i64, ptr %a120
  %t129 = icmp eq i64 %t128, 0
  br i1 %t129, label %then131, label %else132
then131:
  %t134 = load ptr, ptr %a31
  %t135 = getelementptr i8, ptr %t134, i64 24
  store i64 1, ptr %t135, align 1
  store i8 0, ptr %a130
  br label %join133
else132:
  %t136 = load i64, ptr %a120
  %t137 = icmp eq i64 %t136, 1
  br i1 %t137, label %then139, label %else140
then139:
  %t142 = load ptr, ptr %a3
  %t143 = load i64, ptr %a4
  %t144 = mul i64 %t143, 16
  %t145 = add i64 256, %t144
  %t146 = getelementptr i8, ptr %t142, i64 %t145
  %t147 = load i64, ptr %t146, align 1
  %t148 = load ptr, ptr %a37
  %t149 = call i64 @ax_rt_read__seq(i64 %t147, ptr %t148, i64 64)
  store i64 %t149, ptr %a150
  store i8 0, ptr %a138
  br label %join141
else140:
  %t151 = load i64, ptr %a120
  %t152 = sub i64 %t151, 2
  store i64 %t152, ptr %a153
  %t154 = load i64, ptr %a153
  %t155 = icmp slt i64 %t154, 0
  store i1 %t155, ptr %a156
  br i1 %t155, label %join158, label %rhs157
rhs157:
  %t159 = load i64, ptr %a153
  %t160 = load i64, ptr %a106
  %t161 = icmp sge i64 %t159, %t160
  store i1 %t161, ptr %a156
  br label %join158
join158:
  %t162 = load i1, ptr %a156
  br i1 %t162, label %then164, label %else165
then164:
  %t167 = insertvalue %ax_arr undef, ptr @.bytes.34, 0
  %t168 = insertvalue %ax_arr %t167, i64 20, 1
  %t169 = insertvalue %ax_arr %t168, i64 0, 2
  %t170 = extractvalue %ax_arr %t169, 0
  call void @ax_trap(ptr %t170)
  store i8 0, ptr %a163
  br label %join166
else165:
  %t171 = load ptr, ptr %a23
  %t172 = load i64, ptr %a153
  %t173 = mul i64 %t172, 64
  %t174 = getelementptr i8, ptr %t171, i64 %t173
  store ptr %t174, ptr %a175
  %t176 = load ptr, ptr %a175
  %t177 = getelementptr i8, ptr %t176, i64 0
  %t178 = load i64, ptr %t177, align 1
  %t179 = icmp slt i64 %t178, 0
  br i1 %t179, label %then181, label %else182
then181:
  store i8 0, ptr %a180
  br label %join183
else182:
  %t184 = load ptr, ptr %a175
  %t185 = load i64, ptr %a127
  %t186 = load ptr, ptr %a2
  call void @ax_rt_step__seq(ptr %t184, i64 %t185, ptr %t186)
  store i8 0, ptr %a187
  %t188 = load ptr, ptr %a175
  %t189 = getelementptr i8, ptr %t188, i64 0
  %t190 = load i64, ptr %t189, align 1
  %t191 = icmp slt i64 %t190, 0
  br i1 %t191, label %then193, label %else194
then193:
  %t196 = load ptr, ptr %a31
  %t197 = getelementptr i8, ptr %t196, i64 16
  store i64 1, ptr %t197, align 1
  store i8 0, ptr %a192
  br label %join195
else194:
  %t198 = load i64, ptr %a8
  %t199 = load ptr, ptr %a175
  %t200 = load ptr, ptr %a26
  %t201 = load i64, ptr %a153
  call void @ax_rt_epoll_sync__seq(i64 %t198, ptr %t199, ptr %t200, i64 %t201)
  store i8 0, ptr %a192
  br label %join195
join195:
  %t202 = load i8, ptr %a192
  store i8 %t202, ptr %a180
  br label %join183
join183:
  %t203 = load i8, ptr %a180
  store i8 %t203, ptr %a163
  br label %join166
join166:
  %t204 = load i8, ptr %a163
  store i8 %t204, ptr %a138
  br label %join141
join141:
  %t205 = load i8, ptr %a138
  store i8 %t205, ptr %a130
  br label %join133
join133:
  %t206 = load i8, ptr %a130
  store i8 %t206, ptr %a207
  %t208 = load i64, ptr %a107
  %t209 = add i64 %t208, 1
  store i64 %t209, ptr %a107
  br label %loop_cond108
loop_exit110:
  %t210 = load i64, ptr %a107
  store i64 %t210, ptr %a211
  %t212 = load ptr, ptr %a31
  %t213 = getelementptr i8, ptr %t212, i64 16
  %t214 = load i64, ptr %t213, align 1
  %t215 = icmp eq i64 %t214, 0
  br i1 %t215, label %then217, label %else218
then217:
  store i8 0, ptr %a216
  br label %join219
else218:
  %t220 = load i64, ptr %a8
  %t221 = load ptr, ptr %a23
  %t222 = load ptr, ptr %a26
  %t223 = load i64, ptr %a106
  %t224 = call i64 @ax_rt_epoll_compact__seq(i64 %t220, ptr %t221, ptr %t222, i64 %t223)
  store i64 %t224, ptr %a225
  %t226 = load ptr, ptr %a31
  %t227 = load i64, ptr %a225
  %t228 = getelementptr i8, ptr %t226, i64 0
  store i64 %t227, ptr %t228, align 1
  store i8 0, ptr %a216
  br label %join219
join219:
  %t229 = load i8, ptr %a216
  store i8 %t229, ptr %a230
  %t231 = load ptr, ptr %a31
  %t232 = getelementptr i8, ptr %t231, i64 24
  %t233 = load i64, ptr %t232, align 1
  %t234 = icmp eq i64 %t233, 1
  br i1 %t234, label %then236, label %else237
then236:
  %t239 = load i64, ptr %a8
  %t240 = load i64, ptr %a1
  %t241 = load ptr, ptr %a23
  %t242 = load ptr, ptr %a26
  %t243 = load ptr, ptr %a31
  %t244 = load ptr, ptr %a3
  %t245 = load i64, ptr %a4
  %t246 = load i64, ptr %a5
  call void @ax_rt_epoll_accept__seq(i64 %t239, i64 %t240, ptr %t241, ptr %t242, ptr %t243, ptr %t244, i64 %t245, i64 %t246)
  store i8 0, ptr %a235
  br label %join238
else237:
  store i8 0, ptr %a235
  br label %join238
join238:
  %t247 = load i8, ptr %a235
  store i8 %t247, ptr %a248
  store i1 true, ptr %a78
  br label %join81
join81:
  %t249 = load i1, ptr %a78
  store i1 %t249, ptr %a46
  br label %loop_cond47
loop_exit49:
  ret i64 0
}

; rt_serve_worker  graph:abfb036b113a32e2
define internal i64 @ax_rt_serve_worker__seq(i64 %p_listener, ptr %p_handler, ptr %p_control, i64 %p_worker, i64 %p_workers, i64 %p_parent) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca ptr
  %a3 = alloca ptr
  %a4 = alloca i64
  %a5 = alloca i64
  %a6 = alloca i64
  %a12 = alloca ptr
  %a15 = alloca i1
  %a23 = alloca i64
  store i64 %p_listener, ptr %a1
  store ptr %p_handler, ptr %a2
  store ptr %p_control, ptr %a3
  store i64 %p_worker, ptr %a4
  store i64 %p_workers, ptr %a5
  store i64 %p_parent, ptr %a6
  %t7 = insertvalue %ax_arr undef, ptr @.bytes.35, 0
  %t8 = insertvalue %ax_arr %t7, i64 15, 1
  %t9 = insertvalue %ax_arr %t8, i64 0, 2
  %t10 = extractvalue %ax_arr %t9, 0
  %t11 = call ptr @ax_rt_getenv__seq(ptr %t10)
  store ptr %t11, ptr %a12
  %t13 = load ptr, ptr %a12
  %t14 = icmp ne ptr %t13, null
  store i1 %t14, ptr %a15
  br i1 %t14, label %rhs16, label %join17
rhs16:
  %t18 = load ptr, ptr %a12
  %t19 = getelementptr i8, ptr %t18, i64 0
  %t20 = load i8, ptr %t19, align 1
  %t21 = icmp eq i8 %t20, 49
  store i1 %t21, ptr %a15
  br label %join17
join17:
  %t22 = load i1, ptr %a15
  br i1 %t22, label %then24, label %else25
then24:
  %t27 = load i64, ptr %a1
  %t28 = load ptr, ptr %a2
  %t29 = load ptr, ptr %a3
  %t30 = load i64, ptr %a4
  %t31 = load i64, ptr %a5
  %t32 = load i64, ptr %a6
  %t33 = call i64 @ax_rt_http_worker__seq(i64 %t27, ptr %t28, ptr %t29, i64 %t30, i64 %t31, i64 %t32)
  store i64 %t33, ptr %a23
  br label %join26
else25:
  %t34 = load i64, ptr %a1
  %t35 = load ptr, ptr %a2
  %t36 = load ptr, ptr %a3
  %t37 = load i64, ptr %a4
  %t38 = load i64, ptr %a5
  %t39 = load i64, ptr %a6
  %t40 = call i64 @ax_rt_http_epoll_worker__seq(i64 %t34, ptr %t35, ptr %t36, i64 %t37, i64 %t38, i64 %t39)
  store i64 %t40, ptr %a23
  br label %join26
join26:
  %t41 = load i64, ptr %a23
  ret i64 %t41
}

; starts_with  graph:16dd944fe6613e9f
define internal i1 @ax_starts_with__par(%ax_arr %p_a, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a16 = alloca i1
  %a19 = alloca i64
  %a20 = alloca i1
  %a25 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_b, ptr %a4
  %t6 = extractvalue %ax_arr %p_b, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load i64, ptr %a12
  %t14 = load i64, ptr %a9
  %t15 = icmp sle i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  store i64 0, ptr %a19
  store i1 true, ptr %a20
  br label %loop_cond21
loop_cond21:
  %t24 = load i1, ptr %a20
  store i1 %t24, ptr %a25
  br i1 %t24, label %rhs26, label %join27
rhs26:
  %t28 = load i64, ptr %a19
  %t29 = load i64, ptr %a12
  %t30 = icmp slt i64 %t28, %t29
  store i1 %t30, ptr %a25
  br label %join27
join27:
  %t31 = load i1, ptr %a25
  br i1 %t31, label %loop_body22, label %loop_exit23
loop_body22:
  %t32 = load i64, ptr %a19
  %t33 = add i64 %t32, 1
  %t34 = load %ax_arr, ptr %a1
  %t35 = load i64, ptr %a19
  %t36 = extractvalue %ax_arr %t34, 0
  %t37 = extractvalue %ax_arr %t34, 1
  %t38 = getelementptr inbounds i8, ptr %t36, i64 %t35
  %t39 = load i8, ptr %t38
  %t40 = load %ax_arr, ptr %a4
  %t41 = load i64, ptr %a19
  %t42 = extractvalue %ax_arr %t40, 0
  %t43 = extractvalue %ax_arr %t40, 1
  %t44 = getelementptr inbounds i8, ptr %t42, i64 %t41
  %t45 = load i8, ptr %t44
  %t46 = icmp eq i8 %t39, %t45
  store i64 %t33, ptr %a19
  store i1 %t46, ptr %a20
  br label %loop_cond21
loop_exit23:
  %t47 = load i1, ptr %a20
  store i1 %t47, ptr %a16
  br label %join18
join18:
  %t48 = load i1, ptr %a16
  %t49 = load i64, ptr %a2
  %t50 = icmp ne i64 %t49, 0
  %t51 = load %ax_arr, ptr %a1
  br i1 %t50, label %free52, label %cont53
free52:
  %t54 = extractvalue %ax_arr %t51, 0
  %t55 = extractvalue %ax_arr %t51, 1
  %t56 = mul i64 %t55, 1
  call void @ax_free(ptr %t54, i64 %t56)
  br label %cont53
cont53:
  %t57 = load i64, ptr %a5
  %t58 = icmp ne i64 %t57, 0
  %t59 = load %ax_arr, ptr %a4
  br i1 %t58, label %free60, label %cont61
free60:
  %t62 = extractvalue %ax_arr %t59, 0
  %t63 = extractvalue %ax_arr %t59, 1
  %t64 = mul i64 %t63, 1
  call void @ax_free(ptr %t62, i64 %t64)
  br label %cont61
cont61:
  ret i1 %t48
}

; starts_with  graph:16dd944fe6613e9f
define internal i1 @ax_starts_with__seq(%ax_arr %p_a, %ax_arr %p_b) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a16 = alloca i1
  %a19 = alloca i64
  %a20 = alloca i1
  %a25 = alloca i1
  store %ax_arr %p_a, ptr %a1
  %t3 = extractvalue %ax_arr %p_a, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_b, ptr %a4
  %t6 = extractvalue %ax_arr %p_b, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load i64, ptr %a12
  %t14 = load i64, ptr %a9
  %t15 = icmp sle i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  store i64 0, ptr %a19
  store i1 true, ptr %a20
  br label %loop_cond21
loop_cond21:
  %t24 = load i1, ptr %a20
  store i1 %t24, ptr %a25
  br i1 %t24, label %rhs26, label %join27
rhs26:
  %t28 = load i64, ptr %a19
  %t29 = load i64, ptr %a12
  %t30 = icmp slt i64 %t28, %t29
  store i1 %t30, ptr %a25
  br label %join27
join27:
  %t31 = load i1, ptr %a25
  br i1 %t31, label %loop_body22, label %loop_exit23
loop_body22:
  %t32 = load i64, ptr %a19
  %t33 = add i64 %t32, 1
  %t34 = load %ax_arr, ptr %a1
  %t35 = load i64, ptr %a19
  %t36 = extractvalue %ax_arr %t34, 0
  %t37 = extractvalue %ax_arr %t34, 1
  %t38 = getelementptr inbounds i8, ptr %t36, i64 %t35
  %t39 = load i8, ptr %t38
  %t40 = load %ax_arr, ptr %a4
  %t41 = load i64, ptr %a19
  %t42 = extractvalue %ax_arr %t40, 0
  %t43 = extractvalue %ax_arr %t40, 1
  %t44 = getelementptr inbounds i8, ptr %t42, i64 %t41
  %t45 = load i8, ptr %t44
  %t46 = icmp eq i8 %t39, %t45
  store i64 %t33, ptr %a19
  store i1 %t46, ptr %a20
  br label %loop_cond21
loop_exit23:
  %t47 = load i1, ptr %a20
  store i1 %t47, ptr %a16
  br label %join18
join18:
  %t48 = load i1, ptr %a16
  %t49 = load i64, ptr %a2
  %t50 = icmp ne i64 %t49, 0
  %t51 = load %ax_arr, ptr %a1
  br i1 %t50, label %free52, label %cont53
free52:
  %t54 = extractvalue %ax_arr %t51, 0
  %t55 = extractvalue %ax_arr %t51, 1
  %t56 = mul i64 %t55, 1
  call void @ax_free(ptr %t54, i64 %t56)
  br label %cont53
cont53:
  %t57 = load i64, ptr %a5
  %t58 = icmp ne i64 %t57, 0
  %t59 = load %ax_arr, ptr %a4
  br i1 %t58, label %free60, label %cont61
free60:
  %t62 = extractvalue %ax_arr %t59, 0
  %t63 = extractvalue %ax_arr %t59, 1
  %t64 = mul i64 %t63, 1
  call void @ax_free(ptr %t62, i64 %t64)
  br label %cont61
cont61:
  ret i1 %t48
}

; page_count  graph:da29705bd51a9c4e
define internal i64 @ax_page_count__par(%ax_arr %p_req) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a7 = alloca i64
  %a8 = alloca i64
  %a9 = alloca i64
  %a16 = alloca i1
  %a27 = alloca i1
  %a38 = alloca i1
  %a61 = alloca i1
  %a68 = alloca i1
  %a78 = alloca i1
  %a90 = alloca i64
  store %ax_arr %p_req, ptr %a1
  %t3 = extractvalue %ax_arr %p_req, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  store i64 10, ptr %a7
  store i64 0, ptr %a8
  store i64 0, ptr %a9
  br label %loop_cond10
loop_cond10:
  %t13 = load i64, ptr %a7
  %t14 = load i64, ptr %a6
  %t15 = icmp slt i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  %t19 = load %ax_arr, ptr %a1
  %t20 = load i64, ptr %a7
  %t21 = extractvalue %ax_arr %t19, 0
  %t22 = extractvalue %ax_arr %t19, 1
  %t23 = getelementptr inbounds i8, ptr %t21, i64 %t20
  %t24 = load i8, ptr %t23
  %t25 = icmp uge i8 %t24, 48
  store i1 %t25, ptr %a16
  br label %join18
join18:
  %t26 = load i1, ptr %a16
  store i1 %t26, ptr %a27
  br i1 %t26, label %rhs28, label %join29
rhs28:
  %t30 = load %ax_arr, ptr %a1
  %t31 = load i64, ptr %a7
  %t32 = extractvalue %ax_arr %t30, 0
  %t33 = extractvalue %ax_arr %t30, 1
  %t34 = getelementptr inbounds i8, ptr %t32, i64 %t31
  %t35 = load i8, ptr %t34
  %t36 = icmp ule i8 %t35, 57
  store i1 %t36, ptr %a27
  br label %join29
join29:
  %t37 = load i1, ptr %a27
  store i1 %t37, ptr %a38
  br i1 %t37, label %rhs39, label %join40
rhs39:
  %t41 = load i64, ptr %a9
  %t42 = icmp slt i64 %t41, 12
  store i1 %t42, ptr %a38
  br label %join40
join40:
  %t43 = load i1, ptr %a38
  br i1 %t43, label %loop_body11, label %loop_exit12
loop_body11:
  %t44 = load i64, ptr %a7
  %t45 = add i64 %t44, 1
  %t46 = load i64, ptr %a8
  %t47 = mul i64 %t46, 10
  %t48 = load %ax_arr, ptr %a1
  %t49 = load i64, ptr %a7
  %t50 = extractvalue %ax_arr %t48, 0
  %t51 = extractvalue %ax_arr %t48, 1
  %t52 = getelementptr inbounds i8, ptr %t50, i64 %t49
  %t53 = load i8, ptr %t52
  %t54 = zext i8 %t53 to i64
  %t55 = add i64 %t47, %t54
  %t56 = sub i64 %t55, 48
  %t57 = load i64, ptr %a9
  %t58 = add i64 %t57, 1
  store i64 %t45, ptr %a7
  store i64 %t56, ptr %a8
  store i64 %t58, ptr %a9
  br label %loop_cond10
loop_exit12:
  %t59 = load i64, ptr %a9
  %t60 = icmp sgt i64 %t59, 0
  store i1 %t60, ptr %a61
  br i1 %t60, label %rhs62, label %join63
rhs62:
  %t64 = load i64, ptr %a7
  %t65 = load i64, ptr %a6
  %t66 = icmp slt i64 %t64, %t65
  store i1 %t66, ptr %a61
  br label %join63
join63:
  %t67 = load i1, ptr %a61
  store i1 %t67, ptr %a68
  br i1 %t67, label %rhs69, label %join70
rhs69:
  %t71 = load %ax_arr, ptr %a1
  %t72 = load i64, ptr %a7
  %t73 = extractvalue %ax_arr %t71, 0
  %t74 = extractvalue %ax_arr %t71, 1
  %t75 = getelementptr inbounds i8, ptr %t73, i64 %t72
  %t76 = load i8, ptr %t75
  %t77 = icmp eq i8 %t76, 32
  store i1 %t77, ptr %a78
  br i1 %t77, label %join80, label %rhs79
rhs79:
  %t81 = load %ax_arr, ptr %a1
  %t82 = load i64, ptr %a7
  %t83 = extractvalue %ax_arr %t81, 0
  %t84 = extractvalue %ax_arr %t81, 1
  %t85 = getelementptr inbounds i8, ptr %t83, i64 %t82
  %t86 = load i8, ptr %t85
  %t87 = icmp eq i8 %t86, 63
  store i1 %t87, ptr %a78
  br label %join80
join80:
  %t88 = load i1, ptr %a78
  store i1 %t88, ptr %a68
  br label %join70
join70:
  %t89 = load i1, ptr %a68
  br i1 %t89, label %then91, label %else92
then91:
  %t94 = load i64, ptr %a8
  store i64 %t94, ptr %a90
  br label %join93
else92:
  store i64 -1, ptr %a90
  br label %join93
join93:
  %t95 = load i64, ptr %a90
  %t96 = load i64, ptr %a2
  %t97 = icmp ne i64 %t96, 0
  %t98 = load %ax_arr, ptr %a1
  br i1 %t97, label %free99, label %cont100
free99:
  %t101 = extractvalue %ax_arr %t98, 0
  %t102 = extractvalue %ax_arr %t98, 1
  %t103 = mul i64 %t102, 1
  call void @ax_free(ptr %t101, i64 %t103)
  br label %cont100
cont100:
  ret i64 %t95
}

; page_count  graph:da29705bd51a9c4e
define internal i64 @ax_page_count__seq(%ax_arr %p_req) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a7 = alloca i64
  %a8 = alloca i64
  %a9 = alloca i64
  %a16 = alloca i1
  %a27 = alloca i1
  %a38 = alloca i1
  %a61 = alloca i1
  %a68 = alloca i1
  %a78 = alloca i1
  %a90 = alloca i64
  store %ax_arr %p_req, ptr %a1
  %t3 = extractvalue %ax_arr %p_req, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  store i64 10, ptr %a7
  store i64 0, ptr %a8
  store i64 0, ptr %a9
  br label %loop_cond10
loop_cond10:
  %t13 = load i64, ptr %a7
  %t14 = load i64, ptr %a6
  %t15 = icmp slt i64 %t13, %t14
  store i1 %t15, ptr %a16
  br i1 %t15, label %rhs17, label %join18
rhs17:
  %t19 = load %ax_arr, ptr %a1
  %t20 = load i64, ptr %a7
  %t21 = extractvalue %ax_arr %t19, 0
  %t22 = extractvalue %ax_arr %t19, 1
  %t23 = getelementptr inbounds i8, ptr %t21, i64 %t20
  %t24 = load i8, ptr %t23
  %t25 = icmp uge i8 %t24, 48
  store i1 %t25, ptr %a16
  br label %join18
join18:
  %t26 = load i1, ptr %a16
  store i1 %t26, ptr %a27
  br i1 %t26, label %rhs28, label %join29
rhs28:
  %t30 = load %ax_arr, ptr %a1
  %t31 = load i64, ptr %a7
  %t32 = extractvalue %ax_arr %t30, 0
  %t33 = extractvalue %ax_arr %t30, 1
  %t34 = getelementptr inbounds i8, ptr %t32, i64 %t31
  %t35 = load i8, ptr %t34
  %t36 = icmp ule i8 %t35, 57
  store i1 %t36, ptr %a27
  br label %join29
join29:
  %t37 = load i1, ptr %a27
  store i1 %t37, ptr %a38
  br i1 %t37, label %rhs39, label %join40
rhs39:
  %t41 = load i64, ptr %a9
  %t42 = icmp slt i64 %t41, 12
  store i1 %t42, ptr %a38
  br label %join40
join40:
  %t43 = load i1, ptr %a38
  br i1 %t43, label %loop_body11, label %loop_exit12
loop_body11:
  %t44 = load i64, ptr %a7
  %t45 = add i64 %t44, 1
  %t46 = load i64, ptr %a8
  %t47 = mul i64 %t46, 10
  %t48 = load %ax_arr, ptr %a1
  %t49 = load i64, ptr %a7
  %t50 = extractvalue %ax_arr %t48, 0
  %t51 = extractvalue %ax_arr %t48, 1
  %t52 = getelementptr inbounds i8, ptr %t50, i64 %t49
  %t53 = load i8, ptr %t52
  %t54 = zext i8 %t53 to i64
  %t55 = add i64 %t47, %t54
  %t56 = sub i64 %t55, 48
  %t57 = load i64, ptr %a9
  %t58 = add i64 %t57, 1
  store i64 %t45, ptr %a7
  store i64 %t56, ptr %a8
  store i64 %t58, ptr %a9
  br label %loop_cond10
loop_exit12:
  %t59 = load i64, ptr %a9
  %t60 = icmp sgt i64 %t59, 0
  store i1 %t60, ptr %a61
  br i1 %t60, label %rhs62, label %join63
rhs62:
  %t64 = load i64, ptr %a7
  %t65 = load i64, ptr %a6
  %t66 = icmp slt i64 %t64, %t65
  store i1 %t66, ptr %a61
  br label %join63
join63:
  %t67 = load i1, ptr %a61
  store i1 %t67, ptr %a68
  br i1 %t67, label %rhs69, label %join70
rhs69:
  %t71 = load %ax_arr, ptr %a1
  %t72 = load i64, ptr %a7
  %t73 = extractvalue %ax_arr %t71, 0
  %t74 = extractvalue %ax_arr %t71, 1
  %t75 = getelementptr inbounds i8, ptr %t73, i64 %t72
  %t76 = load i8, ptr %t75
  %t77 = icmp eq i8 %t76, 32
  store i1 %t77, ptr %a78
  br i1 %t77, label %join80, label %rhs79
rhs79:
  %t81 = load %ax_arr, ptr %a1
  %t82 = load i64, ptr %a7
  %t83 = extractvalue %ax_arr %t81, 0
  %t84 = extractvalue %ax_arr %t81, 1
  %t85 = getelementptr inbounds i8, ptr %t83, i64 %t82
  %t86 = load i8, ptr %t85
  %t87 = icmp eq i8 %t86, 63
  store i1 %t87, ptr %a78
  br label %join80
join80:
  %t88 = load i1, ptr %a78
  store i1 %t88, ptr %a68
  br label %join70
join70:
  %t89 = load i1, ptr %a68
  br i1 %t89, label %then91, label %else92
then91:
  %t94 = load i64, ptr %a8
  store i64 %t94, ptr %a90
  br label %join93
else92:
  store i64 -1, ptr %a90
  br label %join93
join93:
  %t95 = load i64, ptr %a90
  %t96 = load i64, ptr %a2
  %t97 = icmp ne i64 %t96, 0
  %t98 = load %ax_arr, ptr %a1
  br i1 %t97, label %free99, label %cont100
free99:
  %t101 = extractvalue %ax_arr %t98, 0
  %t102 = extractvalue %ax_arr %t98, 1
  %t103 = mul i64 %t102, 1
  call void @ax_free(ptr %t101, i64 %t103)
  br label %cont100
cont100:
  ret i64 %t95
}

; shift10  graph:fd5f174a17cb3e0c
define internal i64 @ax_shift10__par(i64 %p_v, i64 %p_k) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i64
  store i64 %p_v, ptr %a1
  store i64 %p_k, ptr %a2
  %t3 = load i64, ptr %a1
  store i64 %t3, ptr %a4
  store i64 0, ptr %a5
  br label %loop_cond6
loop_cond6:
  %t9 = load i64, ptr %a5
  %t10 = load i64, ptr %a2
  %t11 = icmp slt i64 %t9, %t10
  br i1 %t11, label %loop_body7, label %loop_exit8
loop_body7:
  %t12 = load i64, ptr %a4
  %t13 = sdiv i64 %t12, 10
  %t14 = load i64, ptr %a5
  %t15 = add i64 %t14, 1
  store i64 %t13, ptr %a4
  store i64 %t15, ptr %a5
  br label %loop_cond6
loop_exit8:
  %t16 = load i64, ptr %a4
  ret i64 %t16
}

; shift10  graph:fd5f174a17cb3e0c
define internal i64 @ax_shift10__seq(i64 %p_v, i64 %p_k) "no-builtins" {
entry:
  %a1 = alloca i64
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i64
  store i64 %p_v, ptr %a1
  store i64 %p_k, ptr %a2
  %t3 = load i64, ptr %a1
  store i64 %t3, ptr %a4
  store i64 0, ptr %a5
  br label %loop_cond6
loop_cond6:
  %t9 = load i64, ptr %a5
  %t10 = load i64, ptr %a2
  %t11 = icmp slt i64 %t9, %t10
  br i1 %t11, label %loop_body7, label %loop_exit8
loop_body7:
  %t12 = load i64, ptr %a4
  %t13 = sdiv i64 %t12, 10
  %t14 = load i64, ptr %a5
  %t15 = add i64 %t14, 1
  store i64 %t13, ptr %a4
  store i64 %t15, ptr %a5
  br label %loop_cond6
loop_exit8:
  %t16 = load i64, ptr %a4
  ret i64 %t16
}

define internal void @ax_utoa__region1(ptr %ctx, i64 %chunk) {
entry:
  %a11 = alloca i64
  %a14 = alloca i64
  %a22 = alloca i64
  %t1 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 0
  %t2 = load i64, ptr %t1
  %t3 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 1
  %t4 = load i64, ptr %t3
  %t5 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 2
  %t6 = load i64, ptr %t5
  %t7 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 3
  %t8 = load %ax_arr, ptr %t7
  %t9 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 4
  %t10 = load i64, ptr %t9
  store i64 %t10, ptr %a11
  %t12 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 5
  %t13 = load i64, ptr %t12
  store i64 %t13, ptr %a14
  %t15 = mul i64 %t4, %chunk
  %t16 = sdiv i64 %t15, %t6
  %t17 = add i64 %t16, %t2
  %t18 = add i64 %chunk, 1
  %t19 = mul i64 %t4, %t18
  %t20 = sdiv i64 %t19, %t6
  %t21 = add i64 %t20, %t2
  store i64 %t17, ptr %a22
  br label %for_cond23
for_cond23:
  %t26 = load i64, ptr %a22
  %t27 = icmp slt i64 %t26, %t21
  br i1 %t27, label %for_body24, label %for_end25
for_body24:
  %t28 = load i64, ptr %a11
  %t29 = load i64, ptr %a14
  %t30 = sub i64 %t29, 1
  %t31 = load i64, ptr %a22
  %t32 = sub i64 %t30, %t31
  %t33 = call i64 @ax_shift10__seq(i64 %t28, i64 %t32)
  %t34 = srem i64 %t33, 10
  %t35 = add i64 48, %t34
  %t36 = trunc i64 %t35 to i8
  %t37 = sub i64 %t26, %t2
  %t38 = extractvalue %ax_arr %t8, 0
  %t39 = extractvalue %ax_arr %t8, 1
  %t40 = getelementptr inbounds i8, ptr %t38, i64 %t37
  store i8 %t36, ptr %t40
  %t41 = add i64 %t26, 1
  store i64 %t41, ptr %a22
  br label %for_cond23
for_end25:
  ret void
}

; utoa  graph:dfda31c6ca797fbe
define internal %ax_arr @ax_utoa__par(i64 %p_v) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca i64
  %a4 = alloca i64
  %a15 = alloca i64
  %a29 = alloca { i64, i64, i64, %ax_arr, i64, i64 }
  store i64 %p_v, ptr %a1
  %t2 = load i64, ptr %a1
  store i64 %t2, ptr %a3
  store i64 1, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load i64, ptr %a3
  %t9 = icmp sge i64 %t8, 10
  br i1 %t9, label %loop_body6, label %loop_exit7
loop_body6:
  %t10 = load i64, ptr %a3
  %t11 = sdiv i64 %t10, 10
  %t12 = load i64, ptr %a4
  %t13 = add i64 %t12, 1
  store i64 %t11, ptr %a3
  store i64 %t13, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t14 = load i64, ptr %a4
  store i64 %t14, ptr %a15
  %t16 = load i64, ptr %a15
  %t17 = sub i64 %t16, 0
  %t18 = icmp slt i64 %t17, 0
  %t19 = select i1 %t18, i64 0, i64 %t17
  %t20 = mul i64 %t19, 1
  %t21 = call ptr @ax_alloc(i64 %t20)
  %t22 = insertvalue %ax_arr undef, ptr %t21, 0
  %t23 = insertvalue %ax_arr %t22, i64 %t19, 1
  %t24 = insertvalue %ax_arr %t23, i64 1, 2
  %t25 = sub i64 %t16, 0
  %t26 = icmp sgt i64 %t16, 0
  %t27 = select i1 %t26, i64 %t25, i64 0
  %t28 = call i64 @ax_chunks(i64 %t27)
  %t30 = load i64, ptr %a1
  %t31 = load i64, ptr %a15
  %t32 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 0
  store i64 0, ptr %t32
  %t33 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 1
  store i64 %t27, ptr %t33
  %t34 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 2
  store i64 %t28, ptr %t34
  %t35 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 3
  store %ax_arr %t24, ptr %t35
  %t36 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 4
  store i64 %t30, ptr %t36
  %t37 = getelementptr inbounds { i64, i64, i64, %ax_arr, i64, i64 }, ptr %a29, i32 0, i32 5
  store i64 %t31, ptr %t37
  call void @ax_par_for(i64 %t28, ptr @ax_utoa__region1, ptr %a29)
  %t38 = insertvalue %ax_arr %t24, i64 1, 2
  ret %ax_arr %t38
}

; utoa  graph:dfda31c6ca797fbe
define internal %ax_arr @ax_utoa__seq(i64 %p_v) "no-builtins" {
entry:
  %a1 = alloca i64
  %a3 = alloca i64
  %a4 = alloca i64
  %a15 = alloca i64
  %a25 = alloca i64
  store i64 %p_v, ptr %a1
  %t2 = load i64, ptr %a1
  store i64 %t2, ptr %a3
  store i64 1, ptr %a4
  br label %loop_cond5
loop_cond5:
  %t8 = load i64, ptr %a3
  %t9 = icmp sge i64 %t8, 10
  br i1 %t9, label %loop_body6, label %loop_exit7
loop_body6:
  %t10 = load i64, ptr %a3
  %t11 = sdiv i64 %t10, 10
  %t12 = load i64, ptr %a4
  %t13 = add i64 %t12, 1
  store i64 %t11, ptr %a3
  store i64 %t13, ptr %a4
  br label %loop_cond5
loop_exit7:
  %t14 = load i64, ptr %a4
  store i64 %t14, ptr %a15
  %t16 = load i64, ptr %a15
  %t17 = sub i64 %t16, 0
  %t18 = icmp slt i64 %t17, 0
  %t19 = select i1 %t18, i64 0, i64 %t17
  %t20 = mul i64 %t19, 1
  %t21 = call ptr @ax_alloc(i64 %t20)
  %t22 = insertvalue %ax_arr undef, ptr %t21, 0
  %t23 = insertvalue %ax_arr %t22, i64 %t19, 1
  %t24 = insertvalue %ax_arr %t23, i64 1, 2
  store i64 0, ptr %a25
  br label %for_cond26
for_cond26:
  %t29 = load i64, ptr %a25
  %t30 = icmp slt i64 %t29, %t16
  br i1 %t30, label %for_body27, label %for_end28
for_body27:
  %t31 = load i64, ptr %a1
  %t32 = load i64, ptr %a15
  %t33 = sub i64 %t32, 1
  %t34 = load i64, ptr %a25
  %t35 = sub i64 %t33, %t34
  %t36 = call i64 @ax_shift10__seq(i64 %t31, i64 %t35)
  %t37 = srem i64 %t36, 10
  %t38 = add i64 48, %t37
  %t39 = trunc i64 %t38 to i8
  %t40 = sub i64 %t29, 0
  %t41 = extractvalue %ax_arr %t24, 0
  %t42 = extractvalue %ax_arr %t24, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  store i8 %t39, ptr %t43
  %t44 = add i64 %t29, 1
  store i64 %t44, ptr %a25
  br label %for_cond26
for_end28:
  %t45 = insertvalue %ax_arr %t24, i64 1, 2
  ret %ax_arr %t45
}

; esc_width  graph:9a6995571fbb8b27
define internal i64 @ax_esc_width__par(i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca i8
  %a4 = alloca i64
  %a10 = alloca i1
  %a16 = alloca i64
  %a22 = alloca i1
  %a28 = alloca i64
  store i8 %p_c, ptr %a1
  %t2 = load i8, ptr %a1
  %t3 = icmp eq i8 %t2, 38
  br i1 %t3, label %then5, label %else6
then5:
  store i64 5, ptr %a4
  br label %join7
else6:
  %t8 = load i8, ptr %a1
  %t9 = icmp eq i8 %t8, 60
  store i1 %t9, ptr %a10
  br i1 %t9, label %join12, label %rhs11
rhs11:
  %t13 = load i8, ptr %a1
  %t14 = icmp eq i8 %t13, 62
  store i1 %t14, ptr %a10
  br label %join12
join12:
  %t15 = load i1, ptr %a10
  br i1 %t15, label %then17, label %else18
then17:
  store i64 4, ptr %a16
  br label %join19
else18:
  %t20 = load i8, ptr %a1
  %t21 = icmp eq i8 %t20, 34
  store i1 %t21, ptr %a22
  br i1 %t21, label %join24, label %rhs23
rhs23:
  %t25 = load i8, ptr %a1
  %t26 = icmp eq i8 %t25, 39
  store i1 %t26, ptr %a22
  br label %join24
join24:
  %t27 = load i1, ptr %a22
  br i1 %t27, label %then29, label %else30
then29:
  store i64 6, ptr %a28
  br label %join31
else30:
  store i64 1, ptr %a28
  br label %join31
join31:
  %t32 = load i64, ptr %a28
  store i64 %t32, ptr %a16
  br label %join19
join19:
  %t33 = load i64, ptr %a16
  store i64 %t33, ptr %a4
  br label %join7
join7:
  %t34 = load i64, ptr %a4
  ret i64 %t34
}

; esc_width  graph:9a6995571fbb8b27
define internal i64 @ax_esc_width__seq(i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca i8
  %a4 = alloca i64
  %a10 = alloca i1
  %a16 = alloca i64
  %a22 = alloca i1
  %a28 = alloca i64
  store i8 %p_c, ptr %a1
  %t2 = load i8, ptr %a1
  %t3 = icmp eq i8 %t2, 38
  br i1 %t3, label %then5, label %else6
then5:
  store i64 5, ptr %a4
  br label %join7
else6:
  %t8 = load i8, ptr %a1
  %t9 = icmp eq i8 %t8, 60
  store i1 %t9, ptr %a10
  br i1 %t9, label %join12, label %rhs11
rhs11:
  %t13 = load i8, ptr %a1
  %t14 = icmp eq i8 %t13, 62
  store i1 %t14, ptr %a10
  br label %join12
join12:
  %t15 = load i1, ptr %a10
  br i1 %t15, label %then17, label %else18
then17:
  store i64 4, ptr %a16
  br label %join19
else18:
  %t20 = load i8, ptr %a1
  %t21 = icmp eq i8 %t20, 34
  store i1 %t21, ptr %a22
  br i1 %t21, label %join24, label %rhs23
rhs23:
  %t25 = load i8, ptr %a1
  %t26 = icmp eq i8 %t25, 39
  store i1 %t26, ptr %a22
  br label %join24
join24:
  %t27 = load i1, ptr %a22
  br i1 %t27, label %then29, label %else30
then29:
  store i64 6, ptr %a28
  br label %join31
else30:
  store i64 1, ptr %a28
  br label %join31
join31:
  %t32 = load i64, ptr %a28
  store i64 %t32, ptr %a16
  br label %join19
join19:
  %t33 = load i64, ptr %a16
  store i64 %t33, ptr %a4
  br label %join7
join7:
  %t34 = load i64, ptr %a4
  ret i64 %t34
}

; put  graph:b186a668275c49a1
define internal %ax_arr @ax_put__par(%ax_arr %p_out, i64 %p_j, %ax_arr %p_s) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a16 = alloca %ax_arr
  %a17 = alloca i64
  %a18 = alloca i64
  %a36 = alloca %ax_arr
  store %ax_arr %p_out, ptr %a1
  %t3 = extractvalue %ax_arr %p_out, 2
  store i64 %t3, ptr %a2
  store i64 %p_j, ptr %a4
  store %ax_arr %p_s, ptr %a5
  %t7 = extractvalue %ax_arr %p_s, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load %ax_arr, ptr %a1
  %t15 = load i64, ptr %a2
  store i64 0, ptr %a2
  store %ax_arr %t14, ptr %a16
  store i64 %t15, ptr %a17
  store i64 0, ptr %a18
  br label %loop_cond19
loop_cond19:
  %t22 = load i64, ptr %a18
  %t23 = load i64, ptr %a13
  %t24 = icmp slt i64 %t22, %t23
  br i1 %t24, label %loop_body20, label %loop_exit21
loop_body20:
  %t25 = load %ax_arr, ptr %a16
  %t26 = load i64, ptr %a17
  store i64 0, ptr %a17
  %t27 = load i64, ptr %a4
  %t28 = load i64, ptr %a18
  %t29 = add i64 %t27, %t28
  %t30 = load %ax_arr, ptr %a5
  %t31 = load i64, ptr %a18
  %t32 = extractvalue %ax_arr %t30, 0
  %t33 = extractvalue %ax_arr %t30, 1
  %t34 = getelementptr inbounds i8, ptr %t32, i64 %t31
  %t35 = load i8, ptr %t34
  %t37 = icmp ne i64 %t26, 0
  br i1 %t37, label %set_inplace38, label %set_copy39
set_copy39:
  %t41 = extractvalue %ax_arr %t25, 1
  %t42 = icmp slt i64 %t41, 0
  %t43 = select i1 %t42, i64 0, i64 %t41
  %t44 = mul i64 %t43, 1
  %t45 = call ptr @ax_alloc(i64 %t44)
  %t46 = insertvalue %ax_arr undef, ptr %t45, 0
  %t47 = insertvalue %ax_arr %t46, i64 %t43, 1
  %t48 = insertvalue %ax_arr %t47, i64 1, 2
  %t49 = mul i64 %t41, 1
  %t50 = extractvalue %ax_arr %t25, 0
  %t51 = extractvalue %ax_arr %t48, 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t51, ptr %t50, i64 %t49, i1 false)
  %t52 = extractvalue %ax_arr %t48, 0
  %t53 = extractvalue %ax_arr %t48, 1
  %t54 = getelementptr inbounds i8, ptr %t52, i64 %t29
  store i8 %t35, ptr %t54
  store %ax_arr %t48, ptr %a36
  br label %set_join40
set_inplace38:
  %t55 = extractvalue %ax_arr %t25, 0
  %t56 = extractvalue %ax_arr %t25, 1
  %t57 = getelementptr inbounds i8, ptr %t55, i64 %t29
  store i8 %t35, ptr %t57
  store %ax_arr %t25, ptr %a36
  br label %set_join40
set_join40:
  %t58 = load %ax_arr, ptr %a36
  %t59 = load i64, ptr %a18
  %t60 = add i64 %t59, 1
  %t61 = load %ax_arr, ptr %a16
  %t62 = load i64, ptr %a17
  %t63 = icmp ne i64 %t62, 0
  br i1 %t63, label %free64, label %cont65
free64:
  %t66 = extractvalue %ax_arr %t61, 0
  %t67 = extractvalue %ax_arr %t61, 1
  %t68 = mul i64 %t67, 1
  call void @ax_free(ptr %t66, i64 %t68)
  br label %cont65
cont65:
  store %ax_arr %t58, ptr %a16
  store i64 1, ptr %a17
  store i64 %t60, ptr %a18
  br label %loop_cond19
loop_exit21:
  %t69 = load %ax_arr, ptr %a16
  %t70 = load i64, ptr %a17
  store i64 0, ptr %a17
  %t71 = icmp ne i64 %t70, 0
  %t72 = load i64, ptr %a17
  %t73 = icmp ne i64 %t72, 0
  %t74 = load %ax_arr, ptr %a16
  %t75 = and i1 %t73, %t71
  br i1 %t75, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t74, 0
  %t79 = extractvalue %ax_arr %t74, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = icmp ne i64 %t70, 0
  %t82 = load i64, ptr %a2
  %t83 = icmp ne i64 %t82, 0
  %t84 = load %ax_arr, ptr %a1
  %t85 = and i1 %t83, %t81
  br i1 %t85, label %free86, label %cont87
free86:
  %t88 = extractvalue %ax_arr %t84, 0
  %t89 = extractvalue %ax_arr %t84, 1
  %t90 = mul i64 %t89, 1
  call void @ax_free(ptr %t88, i64 %t90)
  br label %cont87
cont87:
  %t91 = load i64, ptr %a6
  %t92 = icmp ne i64 %t91, 0
  %t93 = load %ax_arr, ptr %a5
  %t94 = and i1 %t92, %t81
  br i1 %t94, label %free95, label %cont96
free95:
  %t97 = extractvalue %ax_arr %t93, 0
  %t98 = extractvalue %ax_arr %t93, 1
  %t99 = mul i64 %t98, 1
  call void @ax_free(ptr %t97, i64 %t99)
  br label %cont96
cont96:
  %t100 = insertvalue %ax_arr %t69, i64 %t70, 2
  ret %ax_arr %t100
}

; put  graph:b186a668275c49a1
define internal %ax_arr @ax_put__seq(%ax_arr %p_out, i64 %p_j, %ax_arr %p_s) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a10 = alloca i64
  %a13 = alloca i64
  %a16 = alloca %ax_arr
  %a17 = alloca i64
  %a18 = alloca i64
  %a36 = alloca %ax_arr
  store %ax_arr %p_out, ptr %a1
  %t3 = extractvalue %ax_arr %p_out, 2
  store i64 %t3, ptr %a2
  store i64 %p_j, ptr %a4
  store %ax_arr %p_s, ptr %a5
  %t7 = extractvalue %ax_arr %p_s, 2
  store i64 %t7, ptr %a6
  %t8 = load %ax_arr, ptr %a1
  %t9 = extractvalue %ax_arr %t8, 1
  store i64 %t9, ptr %a10
  %t11 = load %ax_arr, ptr %a5
  %t12 = extractvalue %ax_arr %t11, 1
  store i64 %t12, ptr %a13
  %t14 = load %ax_arr, ptr %a1
  %t15 = load i64, ptr %a2
  store i64 0, ptr %a2
  store %ax_arr %t14, ptr %a16
  store i64 %t15, ptr %a17
  store i64 0, ptr %a18
  br label %loop_cond19
loop_cond19:
  %t22 = load i64, ptr %a18
  %t23 = load i64, ptr %a13
  %t24 = icmp slt i64 %t22, %t23
  br i1 %t24, label %loop_body20, label %loop_exit21
loop_body20:
  %t25 = load %ax_arr, ptr %a16
  %t26 = load i64, ptr %a17
  store i64 0, ptr %a17
  %t27 = load i64, ptr %a4
  %t28 = load i64, ptr %a18
  %t29 = add i64 %t27, %t28
  %t30 = load %ax_arr, ptr %a5
  %t31 = load i64, ptr %a18
  %t32 = extractvalue %ax_arr %t30, 0
  %t33 = extractvalue %ax_arr %t30, 1
  %t34 = getelementptr inbounds i8, ptr %t32, i64 %t31
  %t35 = load i8, ptr %t34
  %t37 = icmp ne i64 %t26, 0
  br i1 %t37, label %set_inplace38, label %set_copy39
set_copy39:
  %t41 = extractvalue %ax_arr %t25, 1
  %t42 = icmp slt i64 %t41, 0
  %t43 = select i1 %t42, i64 0, i64 %t41
  %t44 = mul i64 %t43, 1
  %t45 = call ptr @ax_alloc(i64 %t44)
  %t46 = insertvalue %ax_arr undef, ptr %t45, 0
  %t47 = insertvalue %ax_arr %t46, i64 %t43, 1
  %t48 = insertvalue %ax_arr %t47, i64 1, 2
  %t49 = mul i64 %t41, 1
  %t50 = extractvalue %ax_arr %t25, 0
  %t51 = extractvalue %ax_arr %t48, 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t51, ptr %t50, i64 %t49, i1 false)
  %t52 = extractvalue %ax_arr %t48, 0
  %t53 = extractvalue %ax_arr %t48, 1
  %t54 = getelementptr inbounds i8, ptr %t52, i64 %t29
  store i8 %t35, ptr %t54
  store %ax_arr %t48, ptr %a36
  br label %set_join40
set_inplace38:
  %t55 = extractvalue %ax_arr %t25, 0
  %t56 = extractvalue %ax_arr %t25, 1
  %t57 = getelementptr inbounds i8, ptr %t55, i64 %t29
  store i8 %t35, ptr %t57
  store %ax_arr %t25, ptr %a36
  br label %set_join40
set_join40:
  %t58 = load %ax_arr, ptr %a36
  %t59 = load i64, ptr %a18
  %t60 = add i64 %t59, 1
  %t61 = load %ax_arr, ptr %a16
  %t62 = load i64, ptr %a17
  %t63 = icmp ne i64 %t62, 0
  br i1 %t63, label %free64, label %cont65
free64:
  %t66 = extractvalue %ax_arr %t61, 0
  %t67 = extractvalue %ax_arr %t61, 1
  %t68 = mul i64 %t67, 1
  call void @ax_free(ptr %t66, i64 %t68)
  br label %cont65
cont65:
  store %ax_arr %t58, ptr %a16
  store i64 1, ptr %a17
  store i64 %t60, ptr %a18
  br label %loop_cond19
loop_exit21:
  %t69 = load %ax_arr, ptr %a16
  %t70 = load i64, ptr %a17
  store i64 0, ptr %a17
  %t71 = icmp ne i64 %t70, 0
  %t72 = load i64, ptr %a17
  %t73 = icmp ne i64 %t72, 0
  %t74 = load %ax_arr, ptr %a16
  %t75 = and i1 %t73, %t71
  br i1 %t75, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t74, 0
  %t79 = extractvalue %ax_arr %t74, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = icmp ne i64 %t70, 0
  %t82 = load i64, ptr %a2
  %t83 = icmp ne i64 %t82, 0
  %t84 = load %ax_arr, ptr %a1
  %t85 = and i1 %t83, %t81
  br i1 %t85, label %free86, label %cont87
free86:
  %t88 = extractvalue %ax_arr %t84, 0
  %t89 = extractvalue %ax_arr %t84, 1
  %t90 = mul i64 %t89, 1
  call void @ax_free(ptr %t88, i64 %t90)
  br label %cont87
cont87:
  %t91 = load i64, ptr %a6
  %t92 = icmp ne i64 %t91, 0
  %t93 = load %ax_arr, ptr %a5
  %t94 = and i1 %t92, %t81
  br i1 %t94, label %free95, label %cont96
free95:
  %t97 = extractvalue %ax_arr %t93, 0
  %t98 = extractvalue %ax_arr %t93, 1
  %t99 = mul i64 %t98, 1
  call void @ax_free(ptr %t97, i64 %t99)
  br label %cont96
cont96:
  %t100 = insertvalue %ax_arr %t69, i64 %t70, 2
  ret %ax_arr %t100
}

; esc_char  graph:caf0d2881d498df6
define internal %ax_arr @ax_esc_char__par(%ax_arr %p_out, i64 %p_j, i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i8
  %a8 = alloca i64
  %a11 = alloca %ax_arr
  %a12 = alloca i64
  %a28 = alloca %ax_arr
  %a29 = alloca i64
  %a45 = alloca %ax_arr
  %a46 = alloca i64
  %a62 = alloca %ax_arr
  %a63 = alloca i64
  %a79 = alloca %ax_arr
  %a80 = alloca i64
  %a98 = alloca %ax_arr
  store %ax_arr %p_out, ptr %a1
  %t3 = extractvalue %ax_arr %p_out, 2
  store i64 %t3, ptr %a2
  store i64 %p_j, ptr %a4
  store i8 %p_c, ptr %a5
  %t6 = load %ax_arr, ptr %a1
  %t7 = extractvalue %ax_arr %t6, 1
  store i64 %t7, ptr %a8
  %t9 = load i8, ptr %a5
  %t10 = icmp eq i8 %t9, 38
  br i1 %t10, label %then13, label %else14
then13:
  %t16 = load %ax_arr, ptr %a1
  %t17 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t18 = insertvalue %ax_arr %t16, i64 %t17, 2
  %t19 = load i64, ptr %a4
  %t20 = insertvalue %ax_arr undef, ptr @.bytes.36, 0
  %t21 = insertvalue %ax_arr %t20, i64 5, 1
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = insertvalue %ax_arr %t22, i64 0, 2
  %t24 = call %ax_arr @ax_put__par(%ax_arr %t18, i64 %t19, %ax_arr %t23)
  %t25 = extractvalue %ax_arr %t24, 2
  store %ax_arr %t24, ptr %a11
  store i64 %t25, ptr %a12
  br label %join15
else14:
  %t26 = load i8, ptr %a5
  %t27 = icmp eq i8 %t26, 60
  br i1 %t27, label %then30, label %else31
then30:
  %t33 = load %ax_arr, ptr %a1
  %t34 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t35 = insertvalue %ax_arr %t33, i64 %t34, 2
  %t36 = load i64, ptr %a4
  %t37 = insertvalue %ax_arr undef, ptr @.bytes.37, 0
  %t38 = insertvalue %ax_arr %t37, i64 4, 1
  %t39 = insertvalue %ax_arr %t38, i64 0, 2
  %t40 = insertvalue %ax_arr %t39, i64 0, 2
  %t41 = call %ax_arr @ax_put__par(%ax_arr %t35, i64 %t36, %ax_arr %t40)
  %t42 = extractvalue %ax_arr %t41, 2
  store %ax_arr %t41, ptr %a28
  store i64 %t42, ptr %a29
  br label %join32
else31:
  %t43 = load i8, ptr %a5
  %t44 = icmp eq i8 %t43, 62
  br i1 %t44, label %then47, label %else48
then47:
  %t50 = load %ax_arr, ptr %a1
  %t51 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t52 = insertvalue %ax_arr %t50, i64 %t51, 2
  %t53 = load i64, ptr %a4
  %t54 = insertvalue %ax_arr undef, ptr @.bytes.38, 0
  %t55 = insertvalue %ax_arr %t54, i64 4, 1
  %t56 = insertvalue %ax_arr %t55, i64 0, 2
  %t57 = insertvalue %ax_arr %t56, i64 0, 2
  %t58 = call %ax_arr @ax_put__par(%ax_arr %t52, i64 %t53, %ax_arr %t57)
  %t59 = extractvalue %ax_arr %t58, 2
  store %ax_arr %t58, ptr %a45
  store i64 %t59, ptr %a46
  br label %join49
else48:
  %t60 = load i8, ptr %a5
  %t61 = icmp eq i8 %t60, 34
  br i1 %t61, label %then64, label %else65
then64:
  %t67 = load %ax_arr, ptr %a1
  %t68 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t69 = insertvalue %ax_arr %t67, i64 %t68, 2
  %t70 = load i64, ptr %a4
  %t71 = insertvalue %ax_arr undef, ptr @.bytes.39, 0
  %t72 = insertvalue %ax_arr %t71, i64 6, 1
  %t73 = insertvalue %ax_arr %t72, i64 0, 2
  %t74 = insertvalue %ax_arr %t73, i64 0, 2
  %t75 = call %ax_arr @ax_put__par(%ax_arr %t69, i64 %t70, %ax_arr %t74)
  %t76 = extractvalue %ax_arr %t75, 2
  store %ax_arr %t75, ptr %a62
  store i64 %t76, ptr %a63
  br label %join66
else65:
  %t77 = load i8, ptr %a5
  %t78 = icmp eq i8 %t77, 39
  br i1 %t78, label %then81, label %else82
then81:
  %t84 = load %ax_arr, ptr %a1
  %t85 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t86 = insertvalue %ax_arr %t84, i64 %t85, 2
  %t87 = load i64, ptr %a4
  %t88 = insertvalue %ax_arr undef, ptr @.bytes.40, 0
  %t89 = insertvalue %ax_arr %t88, i64 6, 1
  %t90 = insertvalue %ax_arr %t89, i64 0, 2
  %t91 = insertvalue %ax_arr %t90, i64 0, 2
  %t92 = call %ax_arr @ax_put__par(%ax_arr %t86, i64 %t87, %ax_arr %t91)
  %t93 = extractvalue %ax_arr %t92, 2
  store %ax_arr %t92, ptr %a79
  store i64 %t93, ptr %a80
  br label %join83
else82:
  %t94 = load %ax_arr, ptr %a1
  %t95 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t96 = load i64, ptr %a4
  %t97 = load i8, ptr %a5
  %t99 = icmp ne i64 %t95, 0
  br i1 %t99, label %set_inplace100, label %set_copy101
set_copy101:
  %t103 = extractvalue %ax_arr %t94, 1
  %t104 = icmp slt i64 %t103, 0
  %t105 = select i1 %t104, i64 0, i64 %t103
  %t106 = mul i64 %t105, 1
  %t107 = call ptr @ax_alloc(i64 %t106)
  %t108 = insertvalue %ax_arr undef, ptr %t107, 0
  %t109 = insertvalue %ax_arr %t108, i64 %t105, 1
  %t110 = insertvalue %ax_arr %t109, i64 1, 2
  %t111 = mul i64 %t103, 1
  %t112 = extractvalue %ax_arr %t94, 0
  %t113 = extractvalue %ax_arr %t110, 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t113, ptr %t112, i64 %t111, i1 false)
  %t114 = extractvalue %ax_arr %t110, 0
  %t115 = extractvalue %ax_arr %t110, 1
  %t116 = getelementptr inbounds i8, ptr %t114, i64 %t96
  store i8 %t97, ptr %t116
  store %ax_arr %t110, ptr %a98
  br label %set_join102
set_inplace100:
  %t117 = extractvalue %ax_arr %t94, 0
  %t118 = extractvalue %ax_arr %t94, 1
  %t119 = getelementptr inbounds i8, ptr %t117, i64 %t96
  store i8 %t97, ptr %t119
  store %ax_arr %t94, ptr %a98
  br label %set_join102
set_join102:
  %t120 = load %ax_arr, ptr %a98
  store %ax_arr %t120, ptr %a79
  store i64 1, ptr %a80
  br label %join83
join83:
  %t121 = load %ax_arr, ptr %a79
  %t122 = load i64, ptr %a80
  store %ax_arr %t121, ptr %a62
  store i64 %t122, ptr %a63
  br label %join66
join66:
  %t123 = load %ax_arr, ptr %a62
  %t124 = load i64, ptr %a63
  store %ax_arr %t123, ptr %a45
  store i64 %t124, ptr %a46
  br label %join49
join49:
  %t125 = load %ax_arr, ptr %a45
  %t126 = load i64, ptr %a46
  store %ax_arr %t125, ptr %a28
  store i64 %t126, ptr %a29
  br label %join32
join32:
  %t127 = load %ax_arr, ptr %a28
  %t128 = load i64, ptr %a29
  store %ax_arr %t127, ptr %a11
  store i64 %t128, ptr %a12
  br label %join15
join15:
  %t129 = load %ax_arr, ptr %a11
  %t130 = load i64, ptr %a12
  %t131 = icmp ne i64 %t130, 0
  %t132 = load i64, ptr %a2
  %t133 = icmp ne i64 %t132, 0
  %t134 = load %ax_arr, ptr %a1
  %t135 = and i1 %t133, %t131
  br i1 %t135, label %free136, label %cont137
free136:
  %t138 = extractvalue %ax_arr %t134, 0
  %t139 = extractvalue %ax_arr %t134, 1
  %t140 = mul i64 %t139, 1
  call void @ax_free(ptr %t138, i64 %t140)
  br label %cont137
cont137:
  %t141 = insertvalue %ax_arr %t129, i64 %t130, 2
  ret %ax_arr %t141
}

; esc_char  graph:caf0d2881d498df6
define internal %ax_arr @ax_esc_char__seq(%ax_arr %p_out, i64 %p_j, i8 %p_c) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i8
  %a8 = alloca i64
  %a11 = alloca %ax_arr
  %a12 = alloca i64
  %a28 = alloca %ax_arr
  %a29 = alloca i64
  %a45 = alloca %ax_arr
  %a46 = alloca i64
  %a62 = alloca %ax_arr
  %a63 = alloca i64
  %a79 = alloca %ax_arr
  %a80 = alloca i64
  %a98 = alloca %ax_arr
  store %ax_arr %p_out, ptr %a1
  %t3 = extractvalue %ax_arr %p_out, 2
  store i64 %t3, ptr %a2
  store i64 %p_j, ptr %a4
  store i8 %p_c, ptr %a5
  %t6 = load %ax_arr, ptr %a1
  %t7 = extractvalue %ax_arr %t6, 1
  store i64 %t7, ptr %a8
  %t9 = load i8, ptr %a5
  %t10 = icmp eq i8 %t9, 38
  br i1 %t10, label %then13, label %else14
then13:
  %t16 = load %ax_arr, ptr %a1
  %t17 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t18 = insertvalue %ax_arr %t16, i64 %t17, 2
  %t19 = load i64, ptr %a4
  %t20 = insertvalue %ax_arr undef, ptr @.bytes.36, 0
  %t21 = insertvalue %ax_arr %t20, i64 5, 1
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = insertvalue %ax_arr %t22, i64 0, 2
  %t24 = call %ax_arr @ax_put__seq(%ax_arr %t18, i64 %t19, %ax_arr %t23)
  %t25 = extractvalue %ax_arr %t24, 2
  store %ax_arr %t24, ptr %a11
  store i64 %t25, ptr %a12
  br label %join15
else14:
  %t26 = load i8, ptr %a5
  %t27 = icmp eq i8 %t26, 60
  br i1 %t27, label %then30, label %else31
then30:
  %t33 = load %ax_arr, ptr %a1
  %t34 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t35 = insertvalue %ax_arr %t33, i64 %t34, 2
  %t36 = load i64, ptr %a4
  %t37 = insertvalue %ax_arr undef, ptr @.bytes.37, 0
  %t38 = insertvalue %ax_arr %t37, i64 4, 1
  %t39 = insertvalue %ax_arr %t38, i64 0, 2
  %t40 = insertvalue %ax_arr %t39, i64 0, 2
  %t41 = call %ax_arr @ax_put__seq(%ax_arr %t35, i64 %t36, %ax_arr %t40)
  %t42 = extractvalue %ax_arr %t41, 2
  store %ax_arr %t41, ptr %a28
  store i64 %t42, ptr %a29
  br label %join32
else31:
  %t43 = load i8, ptr %a5
  %t44 = icmp eq i8 %t43, 62
  br i1 %t44, label %then47, label %else48
then47:
  %t50 = load %ax_arr, ptr %a1
  %t51 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t52 = insertvalue %ax_arr %t50, i64 %t51, 2
  %t53 = load i64, ptr %a4
  %t54 = insertvalue %ax_arr undef, ptr @.bytes.38, 0
  %t55 = insertvalue %ax_arr %t54, i64 4, 1
  %t56 = insertvalue %ax_arr %t55, i64 0, 2
  %t57 = insertvalue %ax_arr %t56, i64 0, 2
  %t58 = call %ax_arr @ax_put__seq(%ax_arr %t52, i64 %t53, %ax_arr %t57)
  %t59 = extractvalue %ax_arr %t58, 2
  store %ax_arr %t58, ptr %a45
  store i64 %t59, ptr %a46
  br label %join49
else48:
  %t60 = load i8, ptr %a5
  %t61 = icmp eq i8 %t60, 34
  br i1 %t61, label %then64, label %else65
then64:
  %t67 = load %ax_arr, ptr %a1
  %t68 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t69 = insertvalue %ax_arr %t67, i64 %t68, 2
  %t70 = load i64, ptr %a4
  %t71 = insertvalue %ax_arr undef, ptr @.bytes.39, 0
  %t72 = insertvalue %ax_arr %t71, i64 6, 1
  %t73 = insertvalue %ax_arr %t72, i64 0, 2
  %t74 = insertvalue %ax_arr %t73, i64 0, 2
  %t75 = call %ax_arr @ax_put__seq(%ax_arr %t69, i64 %t70, %ax_arr %t74)
  %t76 = extractvalue %ax_arr %t75, 2
  store %ax_arr %t75, ptr %a62
  store i64 %t76, ptr %a63
  br label %join66
else65:
  %t77 = load i8, ptr %a5
  %t78 = icmp eq i8 %t77, 39
  br i1 %t78, label %then81, label %else82
then81:
  %t84 = load %ax_arr, ptr %a1
  %t85 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t86 = insertvalue %ax_arr %t84, i64 %t85, 2
  %t87 = load i64, ptr %a4
  %t88 = insertvalue %ax_arr undef, ptr @.bytes.40, 0
  %t89 = insertvalue %ax_arr %t88, i64 6, 1
  %t90 = insertvalue %ax_arr %t89, i64 0, 2
  %t91 = insertvalue %ax_arr %t90, i64 0, 2
  %t92 = call %ax_arr @ax_put__seq(%ax_arr %t86, i64 %t87, %ax_arr %t91)
  %t93 = extractvalue %ax_arr %t92, 2
  store %ax_arr %t92, ptr %a79
  store i64 %t93, ptr %a80
  br label %join83
else82:
  %t94 = load %ax_arr, ptr %a1
  %t95 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t96 = load i64, ptr %a4
  %t97 = load i8, ptr %a5
  %t99 = icmp ne i64 %t95, 0
  br i1 %t99, label %set_inplace100, label %set_copy101
set_copy101:
  %t103 = extractvalue %ax_arr %t94, 1
  %t104 = icmp slt i64 %t103, 0
  %t105 = select i1 %t104, i64 0, i64 %t103
  %t106 = mul i64 %t105, 1
  %t107 = call ptr @ax_alloc(i64 %t106)
  %t108 = insertvalue %ax_arr undef, ptr %t107, 0
  %t109 = insertvalue %ax_arr %t108, i64 %t105, 1
  %t110 = insertvalue %ax_arr %t109, i64 1, 2
  %t111 = mul i64 %t103, 1
  %t112 = extractvalue %ax_arr %t94, 0
  %t113 = extractvalue %ax_arr %t110, 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t113, ptr %t112, i64 %t111, i1 false)
  %t114 = extractvalue %ax_arr %t110, 0
  %t115 = extractvalue %ax_arr %t110, 1
  %t116 = getelementptr inbounds i8, ptr %t114, i64 %t96
  store i8 %t97, ptr %t116
  store %ax_arr %t110, ptr %a98
  br label %set_join102
set_inplace100:
  %t117 = extractvalue %ax_arr %t94, 0
  %t118 = extractvalue %ax_arr %t94, 1
  %t119 = getelementptr inbounds i8, ptr %t117, i64 %t96
  store i8 %t97, ptr %t119
  store %ax_arr %t94, ptr %a98
  br label %set_join102
set_join102:
  %t120 = load %ax_arr, ptr %a98
  store %ax_arr %t120, ptr %a79
  store i64 1, ptr %a80
  br label %join83
join83:
  %t121 = load %ax_arr, ptr %a79
  %t122 = load i64, ptr %a80
  store %ax_arr %t121, ptr %a62
  store i64 %t122, ptr %a63
  br label %join66
join66:
  %t123 = load %ax_arr, ptr %a62
  %t124 = load i64, ptr %a63
  store %ax_arr %t123, ptr %a45
  store i64 %t124, ptr %a46
  br label %join49
join49:
  %t125 = load %ax_arr, ptr %a45
  %t126 = load i64, ptr %a46
  store %ax_arr %t125, ptr %a28
  store i64 %t126, ptr %a29
  br label %join32
join32:
  %t127 = load %ax_arr, ptr %a28
  %t128 = load i64, ptr %a29
  store %ax_arr %t127, ptr %a11
  store i64 %t128, ptr %a12
  br label %join15
join15:
  %t129 = load %ax_arr, ptr %a11
  %t130 = load i64, ptr %a12
  %t131 = icmp ne i64 %t130, 0
  %t132 = load i64, ptr %a2
  %t133 = icmp ne i64 %t132, 0
  %t134 = load %ax_arr, ptr %a1
  %t135 = and i1 %t133, %t131
  br i1 %t135, label %free136, label %cont137
free136:
  %t138 = extractvalue %ax_arr %t134, 0
  %t139 = extractvalue %ax_arr %t134, 1
  %t140 = mul i64 %t139, 1
  call void @ax_free(ptr %t138, i64 %t140)
  br label %cont137
cont137:
  %t141 = insertvalue %ax_arr %t129, i64 %t130, 2
  ret %ax_arr %t141
}

define internal void @ax_escape__region2(ptr %ctx, i64 %chunk) {
entry:
  %a11 = alloca %ax_arr
  %a14 = alloca i64
  %a22 = alloca i64
  %a23 = alloca i64
  %t1 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 0
  %t2 = load i64, ptr %t1
  %t3 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 1
  %t4 = load i64, ptr %t3
  %t5 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 2
  %t6 = load i64, ptr %t5
  %t7 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 3
  %t8 = load ptr, ptr %t7
  %t9 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 4
  %t10 = load %ax_arr, ptr %t9
  store %ax_arr %t10, ptr %a11
  %t12 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %ctx, i32 0, i32 5
  %t13 = load i64, ptr %t12
  store i64 %t13, ptr %a14
  %t15 = mul i64 %t4, %chunk
  %t16 = sdiv i64 %t15, %t6
  %t17 = add i64 %t16, %t2
  %t18 = add i64 %chunk, 1
  %t19 = mul i64 %t4, %t18
  %t20 = sdiv i64 %t19, %t6
  %t21 = add i64 %t20, %t2
  store i64 0, ptr %a22
  store i64 %t17, ptr %a23
  br label %for_cond24
for_cond24:
  %t27 = load i64, ptr %a23
  %t28 = icmp slt i64 %t27, %t21
  br i1 %t28, label %for_body25, label %for_end26
for_body25:
  %t29 = load %ax_arr, ptr %a11
  %t30 = load i64, ptr %a23
  %t31 = extractvalue %ax_arr %t29, 0
  %t32 = extractvalue %ax_arr %t29, 1
  %t33 = getelementptr inbounds i8, ptr %t31, i64 %t30
  %t34 = load i8, ptr %t33
  %t35 = call i64 @ax_esc_width__seq(i8 %t34)
  %t36 = load i64, ptr %a22
  %t37 = add i64 %t36, %t35
  store i64 %t37, ptr %a22
  %t38 = add i64 %t27, 1
  store i64 %t38, ptr %a23
  br label %for_cond24
for_end26:
  %t39 = getelementptr inbounds i64, ptr %t8, i64 %chunk
  %t40 = load i64, ptr %a22
  store i64 %t40, ptr %t39
  ret void
}

define internal void @ax_escape__region3(ptr %ctx, i64 %chunk) {
entry:
  %a11 = alloca %ax_arr
  %a14 = alloca i64
  %a17 = alloca i64
  %a25 = alloca i64
  %t1 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 0
  %t2 = load i64, ptr %t1
  %t3 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 1
  %t4 = load i64, ptr %t3
  %t5 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 2
  %t6 = load i64, ptr %t5
  %t7 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 3
  %t8 = load %ax_arr, ptr %t7
  %t9 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 4
  %t10 = load %ax_arr, ptr %t9
  store %ax_arr %t10, ptr %a11
  %t12 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 5
  %t13 = load i64, ptr %t12
  store i64 %t13, ptr %a14
  %t15 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %ctx, i32 0, i32 6
  %t16 = load i64, ptr %t15
  store i64 %t16, ptr %a17
  %t18 = mul i64 %t4, %chunk
  %t19 = sdiv i64 %t18, %t6
  %t20 = add i64 %t19, %t2
  %t21 = add i64 %chunk, 1
  %t22 = mul i64 %t4, %t21
  %t23 = sdiv i64 %t22, %t6
  %t24 = add i64 %t23, %t2
  store i64 %t20, ptr %a25
  br label %for_cond26
for_cond26:
  %t29 = load i64, ptr %a25
  %t30 = icmp slt i64 %t29, %t24
  br i1 %t30, label %for_body27, label %for_end28
for_body27:
  %t31 = trunc i64 32 to i8
  %t32 = sub i64 %t29, %t2
  %t33 = extractvalue %ax_arr %t8, 0
  %t34 = extractvalue %ax_arr %t8, 1
  %t35 = getelementptr inbounds i8, ptr %t33, i64 %t32
  store i8 %t31, ptr %t35
  %t36 = add i64 %t29, 1
  store i64 %t36, ptr %a25
  br label %for_cond26
for_end28:
  ret void
}

define internal void @ax_escape__region4(ptr %ctx, i64 %chunk) {
entry:
  %a11 = alloca %ax_arr
  %a14 = alloca i64
  %a17 = alloca i64
  %a20 = alloca %ax_arr
  %a28 = alloca i64
  %t1 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 0
  %t2 = load i64, ptr %t1
  %t3 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 1
  %t4 = load i64, ptr %t3
  %t5 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 2
  %t6 = load i64, ptr %t5
  %t7 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 3
  %t8 = load %ax_arr, ptr %t7
  %t9 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 4
  %t10 = load %ax_arr, ptr %t9
  store %ax_arr %t10, ptr %a11
  %t12 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 5
  %t13 = load i64, ptr %t12
  store i64 %t13, ptr %a14
  %t15 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 6
  %t16 = load i64, ptr %t15
  store i64 %t16, ptr %a17
  %t18 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %ctx, i32 0, i32 7
  %t19 = load %ax_arr, ptr %t18
  store %ax_arr %t19, ptr %a20
  %t21 = mul i64 %t4, %chunk
  %t22 = sdiv i64 %t21, %t6
  %t23 = add i64 %t22, %t2
  %t24 = add i64 %chunk, 1
  %t25 = mul i64 %t4, %t24
  %t26 = sdiv i64 %t25, %t6
  %t27 = add i64 %t26, %t2
  store i64 %t23, ptr %a28
  br label %for_cond29
for_cond29:
  %t32 = load i64, ptr %a28
  %t33 = icmp slt i64 %t32, %t27
  br i1 %t33, label %for_body30, label %for_end31
for_body30:
  %t34 = load %ax_arr, ptr %a20
  %t35 = load i64, ptr %a28
  %t36 = extractvalue %ax_arr %t34, 0
  %t37 = extractvalue %ax_arr %t34, 1
  %t38 = getelementptr inbounds i8, ptr %t36, i64 %t35
  %t39 = load i8, ptr %t38
  %t40 = sub i64 %t32, %t2
  %t41 = extractvalue %ax_arr %t8, 0
  %t42 = extractvalue %ax_arr %t8, 1
  %t43 = getelementptr inbounds i8, ptr %t41, i64 %t40
  store i8 %t39, ptr %t43
  %t44 = add i64 %t32, 1
  store i64 %t44, ptr %a28
  br label %for_cond29
for_end31:
  ret void
}

; escape  graph:e282f479d27dfb28
define internal %ax_arr @ax_escape__par(%ax_arr %p_s) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a8 = alloca i64
  %a15 = alloca { i64, i64, i64, ptr, %ax_arr, i64 }
  %a24 = alloca i64
  %a36 = alloca i64
  %a51 = alloca { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }
  %a62 = alloca %ax_arr
  %a63 = alloca i64
  %a64 = alloca i64
  %a65 = alloca i64
  %a117 = alloca %ax_arr
  %a118 = alloca i64
  %a132 = alloca { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }
  store %ax_arr %p_s, ptr %a1
  %t3 = extractvalue %ax_arr %p_s, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load i64, ptr %a6
  store i64 0, ptr %a8
  %t9 = sub i64 %t7, 0
  %t10 = icmp sgt i64 %t7, 0
  %t11 = select i1 %t10, i64 %t9, i64 0
  %t12 = call i64 @ax_chunks(i64 %t11)
  %t13 = mul i64 %t12, 8
  %t14 = call ptr @ax_alloc(i64 %t13)
  %t16 = load %ax_arr, ptr %a1
  %t17 = load i64, ptr %a6
  %t18 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 0
  store i64 0, ptr %t18
  %t19 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 1
  store i64 %t11, ptr %t19
  %t20 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 2
  store i64 %t12, ptr %t20
  %t21 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 3
  store ptr %t14, ptr %t21
  %t22 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 4
  store %ax_arr %t16, ptr %t22
  %t23 = getelementptr inbounds { i64, i64, i64, ptr, %ax_arr, i64 }, ptr %a15, i32 0, i32 5
  store i64 %t17, ptr %t23
  call void @ax_par_for(i64 %t12, ptr @ax_escape__region2, ptr %a15)
  store i64 0, ptr %a24
  br label %for_cond25
for_cond25:
  %t28 = load i64, ptr %a24
  %t29 = icmp slt i64 %t28, %t12
  br i1 %t29, label %for_body26, label %for_end27
for_body26:
  %t30 = getelementptr inbounds i64, ptr %t14, i64 %t28
  %t31 = load i64, ptr %a8
  %t32 = load i64, ptr %t30
  %t33 = add i64 %t31, %t32
  store i64 %t33, ptr %a8
  %t34 = add i64 %t28, 1
  store i64 %t34, ptr %a24
  br label %for_cond25
for_end27:
  call void @ax_free(ptr %t14, i64 %t13)
  %t35 = load i64, ptr %a8
  store i64 %t35, ptr %a36
  %t37 = load i64, ptr %a6
  %t38 = mul i64 6, %t37
  %t39 = sub i64 %t38, 0
  %t40 = icmp slt i64 %t39, 0
  %t41 = select i1 %t40, i64 0, i64 %t39
  %t42 = mul i64 %t41, 1
  %t43 = call ptr @ax_alloc(i64 %t42)
  %t44 = insertvalue %ax_arr undef, ptr %t43, 0
  %t45 = insertvalue %ax_arr %t44, i64 %t41, 1
  %t46 = insertvalue %ax_arr %t45, i64 1, 2
  %t47 = sub i64 %t38, 0
  %t48 = icmp sgt i64 %t38, 0
  %t49 = select i1 %t48, i64 %t47, i64 0
  %t50 = call i64 @ax_chunks(i64 %t49)
  %t52 = load %ax_arr, ptr %a1
  %t53 = load i64, ptr %a6
  %t54 = load i64, ptr %a36
  %t55 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 0
  store i64 0, ptr %t55
  %t56 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 1
  store i64 %t49, ptr %t56
  %t57 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 2
  store i64 %t50, ptr %t57
  %t58 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 3
  store %ax_arr %t46, ptr %t58
  %t59 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 4
  store %ax_arr %t52, ptr %t59
  %t60 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 5
  store i64 %t53, ptr %t60
  %t61 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64 }, ptr %a51, i32 0, i32 6
  store i64 %t54, ptr %t61
  call void @ax_par_for(i64 %t50, ptr @ax_escape__region3, ptr %a51)
  store %ax_arr %t46, ptr %a62
  store i64 1, ptr %a63
  store i64 0, ptr %a64
  store i64 0, ptr %a65
  br label %loop_cond66
loop_cond66:
  %t69 = load i64, ptr %a64
  %t70 = load i64, ptr %a6
  %t71 = icmp slt i64 %t69, %t70
  br i1 %t71, label %loop_body67, label %loop_exit68
loop_body67:
  %t72 = load %ax_arr, ptr %a62
  %t73 = load i64, ptr %a63
  store i64 0, ptr %a63
  %t74 = insertvalue %ax_arr %t72, i64 %t73, 2
  %t75 = load i64, ptr %a65
  %t76 = load %ax_arr, ptr %a1
  %t77 = load i64, ptr %a64
  %t78 = extractvalue %ax_arr %t76, 0
  %t79 = extractvalue %ax_arr %t76, 1
  %t80 = getelementptr inbounds i8, ptr %t78, i64 %t77
  %t81 = load i8, ptr %t80
  %t82 = call %ax_arr @ax_esc_char__par(%ax_arr %t74, i64 %t75, i8 %t81)
  %t83 = extractvalue %ax_arr %t82, 2
  %t84 = load i64, ptr %a64
  %t85 = add i64 %t84, 1
  %t86 = load i64, ptr %a65
  %t87 = load %ax_arr, ptr %a1
  %t88 = load i64, ptr %a64
  %t89 = extractvalue %ax_arr %t87, 0
  %t90 = extractvalue %ax_arr %t87, 1
  %t91 = getelementptr inbounds i8, ptr %t89, i64 %t88
  %t92 = load i8, ptr %t91
  %t93 = call i64 @ax_esc_width__par(i8 %t92)
  %t94 = add i64 %t86, %t93
  %t95 = icmp ne i64 %t83, 0
  %t96 = load %ax_arr, ptr %a62
  %t97 = load i64, ptr %a63
  %t98 = icmp ne i64 %t97, 0
  %t99 = and i1 %t98, %t95
  br i1 %t99, label %free100, label %cont101
free100:
  %t102 = extractvalue %ax_arr %t96, 0
  %t103 = extractvalue %ax_arr %t96, 1
  %t104 = mul i64 %t103, 1
  call void @ax_free(ptr %t102, i64 %t104)
  br label %cont101
cont101:
  store %ax_arr %t82, ptr %a62
  store i64 %t83, ptr %a63
  store i64 %t85, ptr %a64
  store i64 %t94, ptr %a65
  br label %loop_cond66
loop_exit68:
  %t105 = load %ax_arr, ptr %a62
  %t106 = load i64, ptr %a63
  store i64 0, ptr %a63
  %t107 = icmp ne i64 %t106, 0
  %t108 = load i64, ptr %a63
  %t109 = icmp ne i64 %t108, 0
  %t110 = load %ax_arr, ptr %a62
  %t111 = and i1 %t109, %t107
  br i1 %t111, label %free112, label %cont113
free112:
  %t114 = extractvalue %ax_arr %t110, 0
  %t115 = extractvalue %ax_arr %t110, 1
  %t116 = mul i64 %t115, 1
  call void @ax_free(ptr %t114, i64 %t116)
  br label %cont113
cont113:
  store %ax_arr %t105, ptr %a117
  store i64 %t106, ptr %a118
  %t119 = load i64, ptr %a36
  %t120 = sub i64 %t119, 0
  %t121 = icmp slt i64 %t120, 0
  %t122 = select i1 %t121, i64 0, i64 %t120
  %t123 = mul i64 %t122, 1
  %t124 = call ptr @ax_alloc(i64 %t123)
  %t125 = insertvalue %ax_arr undef, ptr %t124, 0
  %t126 = insertvalue %ax_arr %t125, i64 %t122, 1
  %t127 = insertvalue %ax_arr %t126, i64 1, 2
  %t128 = sub i64 %t119, 0
  %t129 = icmp sgt i64 %t119, 0
  %t130 = select i1 %t129, i64 %t128, i64 0
  %t131 = call i64 @ax_chunks(i64 %t130)
  %t133 = load %ax_arr, ptr %a1
  %t134 = load i64, ptr %a6
  %t135 = load i64, ptr %a36
  %t136 = load %ax_arr, ptr %a117
  %t137 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 0
  store i64 0, ptr %t137
  %t138 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 1
  store i64 %t130, ptr %t138
  %t139 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 2
  store i64 %t131, ptr %t139
  %t140 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 3
  store %ax_arr %t127, ptr %t140
  %t141 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 4
  store %ax_arr %t133, ptr %t141
  %t142 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 5
  store i64 %t134, ptr %t142
  %t143 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 6
  store i64 %t135, ptr %t143
  %t144 = getelementptr inbounds { i64, i64, i64, %ax_arr, %ax_arr, i64, i64, %ax_arr }, ptr %a132, i32 0, i32 7
  store %ax_arr %t136, ptr %t144
  call void @ax_par_for(i64 %t131, ptr @ax_escape__region4, ptr %a132)
  %t145 = load i64, ptr %a118
  %t146 = icmp ne i64 %t145, 0
  %t147 = load %ax_arr, ptr %a117
  br i1 %t146, label %free148, label %cont149
free148:
  %t150 = extractvalue %ax_arr %t147, 0
  %t151 = extractvalue %ax_arr %t147, 1
  %t152 = mul i64 %t151, 1
  call void @ax_free(ptr %t150, i64 %t152)
  br label %cont149
cont149:
  %t153 = load i64, ptr %a2
  %t154 = icmp ne i64 %t153, 0
  %t155 = load %ax_arr, ptr %a1
  br i1 %t154, label %free156, label %cont157
free156:
  %t158 = extractvalue %ax_arr %t155, 0
  %t159 = extractvalue %ax_arr %t155, 1
  %t160 = mul i64 %t159, 1
  call void @ax_free(ptr %t158, i64 %t160)
  br label %cont157
cont157:
  %t161 = insertvalue %ax_arr %t127, i64 1, 2
  ret %ax_arr %t161
}

; escape  graph:e282f479d27dfb28
define internal %ax_arr @ax_escape__seq(%ax_arr %p_s) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a8 = alloca i64
  %a9 = alloca i64
  %a26 = alloca i64
  %a37 = alloca i64
  %a49 = alloca %ax_arr
  %a50 = alloca i64
  %a51 = alloca i64
  %a52 = alloca i64
  %a104 = alloca %ax_arr
  %a105 = alloca i64
  %a115 = alloca i64
  store %ax_arr %p_s, ptr %a1
  %t3 = extractvalue %ax_arr %p_s, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load i64, ptr %a6
  store i64 0, ptr %a8
  store i64 0, ptr %a9
  br label %for_cond10
for_cond10:
  %t13 = load i64, ptr %a9
  %t14 = icmp slt i64 %t13, %t7
  br i1 %t14, label %for_body11, label %for_end12
for_body11:
  %t15 = load %ax_arr, ptr %a1
  %t16 = load i64, ptr %a9
  %t17 = extractvalue %ax_arr %t15, 0
  %t18 = extractvalue %ax_arr %t15, 1
  %t19 = getelementptr inbounds i8, ptr %t17, i64 %t16
  %t20 = load i8, ptr %t19
  %t21 = call i64 @ax_esc_width__seq(i8 %t20)
  %t22 = load i64, ptr %a8
  %t23 = add i64 %t22, %t21
  store i64 %t23, ptr %a8
  %t24 = add i64 %t13, 1
  store i64 %t24, ptr %a9
  br label %for_cond10
for_end12:
  %t25 = load i64, ptr %a8
  store i64 %t25, ptr %a26
  %t27 = load i64, ptr %a6
  %t28 = mul i64 6, %t27
  %t29 = sub i64 %t28, 0
  %t30 = icmp slt i64 %t29, 0
  %t31 = select i1 %t30, i64 0, i64 %t29
  %t32 = mul i64 %t31, 1
  %t33 = call ptr @ax_alloc(i64 %t32)
  %t34 = insertvalue %ax_arr undef, ptr %t33, 0
  %t35 = insertvalue %ax_arr %t34, i64 %t31, 1
  %t36 = insertvalue %ax_arr %t35, i64 1, 2
  store i64 0, ptr %a37
  br label %for_cond38
for_cond38:
  %t41 = load i64, ptr %a37
  %t42 = icmp slt i64 %t41, %t28
  br i1 %t42, label %for_body39, label %for_end40
for_body39:
  %t43 = trunc i64 32 to i8
  %t44 = sub i64 %t41, 0
  %t45 = extractvalue %ax_arr %t36, 0
  %t46 = extractvalue %ax_arr %t36, 1
  %t47 = getelementptr inbounds i8, ptr %t45, i64 %t44
  store i8 %t43, ptr %t47
  %t48 = add i64 %t41, 1
  store i64 %t48, ptr %a37
  br label %for_cond38
for_end40:
  store %ax_arr %t36, ptr %a49
  store i64 1, ptr %a50
  store i64 0, ptr %a51
  store i64 0, ptr %a52
  br label %loop_cond53
loop_cond53:
  %t56 = load i64, ptr %a51
  %t57 = load i64, ptr %a6
  %t58 = icmp slt i64 %t56, %t57
  br i1 %t58, label %loop_body54, label %loop_exit55
loop_body54:
  %t59 = load %ax_arr, ptr %a49
  %t60 = load i64, ptr %a50
  store i64 0, ptr %a50
  %t61 = insertvalue %ax_arr %t59, i64 %t60, 2
  %t62 = load i64, ptr %a52
  %t63 = load %ax_arr, ptr %a1
  %t64 = load i64, ptr %a51
  %t65 = extractvalue %ax_arr %t63, 0
  %t66 = extractvalue %ax_arr %t63, 1
  %t67 = getelementptr inbounds i8, ptr %t65, i64 %t64
  %t68 = load i8, ptr %t67
  %t69 = call %ax_arr @ax_esc_char__seq(%ax_arr %t61, i64 %t62, i8 %t68)
  %t70 = extractvalue %ax_arr %t69, 2
  %t71 = load i64, ptr %a51
  %t72 = add i64 %t71, 1
  %t73 = load i64, ptr %a52
  %t74 = load %ax_arr, ptr %a1
  %t75 = load i64, ptr %a51
  %t76 = extractvalue %ax_arr %t74, 0
  %t77 = extractvalue %ax_arr %t74, 1
  %t78 = getelementptr inbounds i8, ptr %t76, i64 %t75
  %t79 = load i8, ptr %t78
  %t80 = call i64 @ax_esc_width__seq(i8 %t79)
  %t81 = add i64 %t73, %t80
  %t82 = icmp ne i64 %t70, 0
  %t83 = load %ax_arr, ptr %a49
  %t84 = load i64, ptr %a50
  %t85 = icmp ne i64 %t84, 0
  %t86 = and i1 %t85, %t82
  br i1 %t86, label %free87, label %cont88
free87:
  %t89 = extractvalue %ax_arr %t83, 0
  %t90 = extractvalue %ax_arr %t83, 1
  %t91 = mul i64 %t90, 1
  call void @ax_free(ptr %t89, i64 %t91)
  br label %cont88
cont88:
  store %ax_arr %t69, ptr %a49
  store i64 %t70, ptr %a50
  store i64 %t72, ptr %a51
  store i64 %t81, ptr %a52
  br label %loop_cond53
loop_exit55:
  %t92 = load %ax_arr, ptr %a49
  %t93 = load i64, ptr %a50
  store i64 0, ptr %a50
  %t94 = icmp ne i64 %t93, 0
  %t95 = load i64, ptr %a50
  %t96 = icmp ne i64 %t95, 0
  %t97 = load %ax_arr, ptr %a49
  %t98 = and i1 %t96, %t94
  br i1 %t98, label %free99, label %cont100
free99:
  %t101 = extractvalue %ax_arr %t97, 0
  %t102 = extractvalue %ax_arr %t97, 1
  %t103 = mul i64 %t102, 1
  call void @ax_free(ptr %t101, i64 %t103)
  br label %cont100
cont100:
  store %ax_arr %t92, ptr %a104
  store i64 %t93, ptr %a105
  %t106 = load i64, ptr %a26
  %t107 = sub i64 %t106, 0
  %t108 = icmp slt i64 %t107, 0
  %t109 = select i1 %t108, i64 0, i64 %t107
  %t110 = mul i64 %t109, 1
  %t111 = call ptr @ax_alloc(i64 %t110)
  %t112 = insertvalue %ax_arr undef, ptr %t111, 0
  %t113 = insertvalue %ax_arr %t112, i64 %t109, 1
  %t114 = insertvalue %ax_arr %t113, i64 1, 2
  store i64 0, ptr %a115
  br label %for_cond116
for_cond116:
  %t119 = load i64, ptr %a115
  %t120 = icmp slt i64 %t119, %t106
  br i1 %t120, label %for_body117, label %for_end118
for_body117:
  %t121 = load %ax_arr, ptr %a104
  %t122 = load i64, ptr %a115
  %t123 = extractvalue %ax_arr %t121, 0
  %t124 = extractvalue %ax_arr %t121, 1
  %t125 = getelementptr inbounds i8, ptr %t123, i64 %t122
  %t126 = load i8, ptr %t125
  %t127 = sub i64 %t119, 0
  %t128 = extractvalue %ax_arr %t114, 0
  %t129 = extractvalue %ax_arr %t114, 1
  %t130 = getelementptr inbounds i8, ptr %t128, i64 %t127
  store i8 %t126, ptr %t130
  %t131 = add i64 %t119, 1
  store i64 %t131, ptr %a115
  br label %for_cond116
for_end118:
  %t132 = load i64, ptr %a105
  %t133 = icmp ne i64 %t132, 0
  %t134 = load %ax_arr, ptr %a104
  br i1 %t133, label %free135, label %cont136
free135:
  %t137 = extractvalue %ax_arr %t134, 0
  %t138 = extractvalue %ax_arr %t134, 1
  %t139 = mul i64 %t138, 1
  call void @ax_free(ptr %t137, i64 %t139)
  br label %cont136
cont136:
  %t140 = load i64, ptr %a2
  %t141 = icmp ne i64 %t140, 0
  %t142 = load %ax_arr, ptr %a1
  br i1 %t141, label %free143, label %cont144
free143:
  %t145 = extractvalue %ax_arr %t142, 0
  %t146 = extractvalue %ax_arr %t142, 1
  %t147 = mul i64 %t146, 1
  call void @ax_free(ptr %t145, i64 %t147)
  br label %cont144
cont144:
  %t148 = insertvalue %ax_arr %t114, i64 1, 2
  ret %ax_arr %t148
}

; jsx_Badge  graph:096dff57aa99595a
define internal %ax_arr @ax_jsx_Badge__par(%ax_arr %p_p_label) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a21 = alloca %ax_arr
  store %ax_arr %p_p_label, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_label, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = insertvalue %ax_arr undef, ptr @.bytes.41, 0
  %t8 = insertvalue %ax_arr %t7, i64 20, 1
  %t9 = insertvalue %ax_arr %t8, i64 0, 2
  %t10 = load %ax_arr, ptr %a1
  %t11 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t12 = insertvalue %ax_arr %t10, i64 %t11, 2
  %t13 = call %ax_arr @ax_escape__par(%ax_arr %t12)
  %t14 = extractvalue %ax_arr %t13, 2
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.42, 0
  %t16 = insertvalue %ax_arr %t15, i64 7, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = extractvalue %ax_arr %t13, 1
  %t19 = add i64 20, %t18
  %t20 = add i64 %t19, 7
  br label %cat_fresh23
cat_fresh23:
  %t25 = icmp slt i64 %t20, 0
  %t26 = select i1 %t25, i64 0, i64 %t20
  %t27 = mul i64 %t26, 1
  %t28 = call ptr @ax_alloc(i64 %t27)
  %t29 = insertvalue %ax_arr undef, ptr %t28, 0
  %t30 = insertvalue %ax_arr %t29, i64 %t26, 1
  %t31 = insertvalue %ax_arr %t30, i64 1, 2
  %t32 = extractvalue %ax_arr %t31, 0
  %t33 = extractvalue %ax_arr %t9, 0
  %t34 = getelementptr inbounds i8, ptr %t32, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t34, ptr %t33, i64 20, i1 false)
  %t35 = add i64 0, 20
  %t36 = extractvalue %ax_arr %t13, 0
  %t37 = getelementptr inbounds i8, ptr %t32, i64 %t35
  call void @llvm.memcpy.p0.p0.i64(ptr %t37, ptr %t36, i64 %t18, i1 false)
  %t38 = add i64 %t35, %t18
  %t39 = icmp ne i64 %t14, 0
  br i1 %t39, label %free40, label %cont41
free40:
  %t42 = extractvalue %ax_arr %t13, 0
  %t43 = extractvalue %ax_arr %t13, 1
  %t44 = mul i64 %t43, 1
  call void @ax_free(ptr %t42, i64 %t44)
  br label %cont41
cont41:
  %t45 = extractvalue %ax_arr %t17, 0
  %t46 = getelementptr inbounds i8, ptr %t32, i64 %t38
  call void @llvm.memcpy.p0.p0.i64(ptr %t46, ptr %t45, i64 7, i1 false)
  %t47 = add i64 %t38, 7
  store %ax_arr %t31, ptr %a21
  br label %cat_join24
cat_join24:
  %t48 = load %ax_arr, ptr %a21
  %t49 = load i64, ptr %a2
  %t50 = icmp ne i64 %t49, 0
  %t51 = load %ax_arr, ptr %a1
  br i1 %t50, label %free52, label %cont53
free52:
  %t54 = extractvalue %ax_arr %t51, 0
  %t55 = extractvalue %ax_arr %t51, 1
  %t56 = mul i64 %t55, 1
  call void @ax_free(ptr %t54, i64 %t56)
  br label %cont53
cont53:
  %t57 = insertvalue %ax_arr %t48, i64 1, 2
  ret %ax_arr %t57
}

; jsx_Badge  graph:096dff57aa99595a
define internal %ax_arr @ax_jsx_Badge__seq(%ax_arr %p_p_label) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a21 = alloca %ax_arr
  store %ax_arr %p_p_label, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_label, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = insertvalue %ax_arr undef, ptr @.bytes.41, 0
  %t8 = insertvalue %ax_arr %t7, i64 20, 1
  %t9 = insertvalue %ax_arr %t8, i64 0, 2
  %t10 = load %ax_arr, ptr %a1
  %t11 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t12 = insertvalue %ax_arr %t10, i64 %t11, 2
  %t13 = call %ax_arr @ax_escape__seq(%ax_arr %t12)
  %t14 = extractvalue %ax_arr %t13, 2
  %t15 = insertvalue %ax_arr undef, ptr @.bytes.42, 0
  %t16 = insertvalue %ax_arr %t15, i64 7, 1
  %t17 = insertvalue %ax_arr %t16, i64 0, 2
  %t18 = extractvalue %ax_arr %t13, 1
  %t19 = add i64 20, %t18
  %t20 = add i64 %t19, 7
  br label %cat_fresh23
cat_fresh23:
  %t25 = icmp slt i64 %t20, 0
  %t26 = select i1 %t25, i64 0, i64 %t20
  %t27 = mul i64 %t26, 1
  %t28 = call ptr @ax_alloc(i64 %t27)
  %t29 = insertvalue %ax_arr undef, ptr %t28, 0
  %t30 = insertvalue %ax_arr %t29, i64 %t26, 1
  %t31 = insertvalue %ax_arr %t30, i64 1, 2
  %t32 = extractvalue %ax_arr %t31, 0
  %t33 = extractvalue %ax_arr %t9, 0
  %t34 = getelementptr inbounds i8, ptr %t32, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t34, ptr %t33, i64 20, i1 false)
  %t35 = add i64 0, 20
  %t36 = extractvalue %ax_arr %t13, 0
  %t37 = getelementptr inbounds i8, ptr %t32, i64 %t35
  call void @llvm.memcpy.p0.p0.i64(ptr %t37, ptr %t36, i64 %t18, i1 false)
  %t38 = add i64 %t35, %t18
  %t39 = icmp ne i64 %t14, 0
  br i1 %t39, label %free40, label %cont41
free40:
  %t42 = extractvalue %ax_arr %t13, 0
  %t43 = extractvalue %ax_arr %t13, 1
  %t44 = mul i64 %t43, 1
  call void @ax_free(ptr %t42, i64 %t44)
  br label %cont41
cont41:
  %t45 = extractvalue %ax_arr %t17, 0
  %t46 = getelementptr inbounds i8, ptr %t32, i64 %t38
  call void @llvm.memcpy.p0.p0.i64(ptr %t46, ptr %t45, i64 7, i1 false)
  %t47 = add i64 %t38, 7
  store %ax_arr %t31, ptr %a21
  br label %cat_join24
cat_join24:
  %t48 = load %ax_arr, ptr %a21
  %t49 = load i64, ptr %a2
  %t50 = icmp ne i64 %t49, 0
  %t51 = load %ax_arr, ptr %a1
  br i1 %t50, label %free52, label %cont53
free52:
  %t54 = extractvalue %ax_arr %t51, 0
  %t55 = extractvalue %ax_arr %t51, 1
  %t56 = mul i64 %t55, 1
  call void @ax_free(ptr %t54, i64 %t56)
  br label %cont53
cont53:
  %t57 = insertvalue %ax_arr %t48, i64 1, 2
  ret %ax_arr %t57
}

; jsx_Card  graph:439ae9a24f80e55e
define internal %ax_arr @ax_jsx_Card__par(%ax_arr %p_p_title, %ax_arr %p_p_children) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a18 = alloca %ax_arr
  %a19 = alloca i64
  %a45 = alloca %ax_arr
  store %ax_arr %p_p_title, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_title, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_p_children, ptr %a4
  %t6 = extractvalue %ax_arr %p_p_children, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load %ax_arr, ptr %a1
  %t14 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t15 = insertvalue %ax_arr %t13, i64 %t14, 2
  %t16 = call %ax_arr @ax_escape__par(%ax_arr %t15)
  %t17 = extractvalue %ax_arr %t16, 2
  store %ax_arr %t16, ptr %a18
  store i64 %t17, ptr %a19
  %t20 = insertvalue %ax_arr undef, ptr @.bytes.43, 0
  %t21 = insertvalue %ax_arr %t20, i64 29, 1
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = load %ax_arr, ptr %a18
  %t24 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t25 = insertvalue %ax_arr %t24, i64 6, 1
  %t26 = insertvalue %ax_arr %t25, i64 0, 2
  %t27 = load %ax_arr, ptr %a18
  %t28 = insertvalue %ax_arr undef, ptr @.bytes.45, 0
  %t29 = insertvalue %ax_arr %t28, i64 10, 1
  %t30 = insertvalue %ax_arr %t29, i64 0, 2
  %t31 = load %ax_arr, ptr %a4
  %t32 = load i64, ptr %a5
  store i64 0, ptr %a5
  %t33 = insertvalue %ax_arr undef, ptr @.bytes.46, 0
  %t34 = insertvalue %ax_arr %t33, i64 16, 1
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = extractvalue %ax_arr %t23, 1
  %t37 = extractvalue %ax_arr %t27, 1
  %t38 = extractvalue %ax_arr %t31, 1
  %t39 = add i64 29, %t36
  %t40 = add i64 %t39, 6
  %t41 = add i64 %t40, %t37
  %t42 = add i64 %t41, 10
  %t43 = add i64 %t42, %t38
  %t44 = add i64 %t43, 16
  br label %cat_fresh47
cat_fresh47:
  %t49 = icmp slt i64 %t44, 0
  %t50 = select i1 %t49, i64 0, i64 %t44
  %t51 = mul i64 %t50, 1
  %t52 = call ptr @ax_alloc(i64 %t51)
  %t53 = insertvalue %ax_arr undef, ptr %t52, 0
  %t54 = insertvalue %ax_arr %t53, i64 %t50, 1
  %t55 = insertvalue %ax_arr %t54, i64 1, 2
  %t56 = extractvalue %ax_arr %t55, 0
  %t57 = extractvalue %ax_arr %t22, 0
  %t58 = getelementptr inbounds i8, ptr %t56, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t58, ptr %t57, i64 29, i1 false)
  %t59 = add i64 0, 29
  %t60 = extractvalue %ax_arr %t23, 0
  %t61 = getelementptr inbounds i8, ptr %t56, i64 %t59
  call void @llvm.memcpy.p0.p0.i64(ptr %t61, ptr %t60, i64 %t36, i1 false)
  %t62 = add i64 %t59, %t36
  %t63 = extractvalue %ax_arr %t26, 0
  %t64 = getelementptr inbounds i8, ptr %t56, i64 %t62
  call void @llvm.memcpy.p0.p0.i64(ptr %t64, ptr %t63, i64 6, i1 false)
  %t65 = add i64 %t62, 6
  %t66 = extractvalue %ax_arr %t27, 0
  %t67 = getelementptr inbounds i8, ptr %t56, i64 %t65
  call void @llvm.memcpy.p0.p0.i64(ptr %t67, ptr %t66, i64 %t37, i1 false)
  %t68 = add i64 %t65, %t37
  %t69 = extractvalue %ax_arr %t30, 0
  %t70 = getelementptr inbounds i8, ptr %t56, i64 %t68
  call void @llvm.memcpy.p0.p0.i64(ptr %t70, ptr %t69, i64 10, i1 false)
  %t71 = add i64 %t68, 10
  %t72 = extractvalue %ax_arr %t31, 0
  %t73 = getelementptr inbounds i8, ptr %t56, i64 %t71
  call void @llvm.memcpy.p0.p0.i64(ptr %t73, ptr %t72, i64 %t38, i1 false)
  %t74 = add i64 %t71, %t38
  %t75 = icmp ne i64 %t32, 0
  br i1 %t75, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t31, 0
  %t79 = extractvalue %ax_arr %t31, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = extractvalue %ax_arr %t35, 0
  %t82 = getelementptr inbounds i8, ptr %t56, i64 %t74
  call void @llvm.memcpy.p0.p0.i64(ptr %t82, ptr %t81, i64 16, i1 false)
  %t83 = add i64 %t74, 16
  store %ax_arr %t55, ptr %a45
  br label %cat_join48
cat_join48:
  %t84 = load %ax_arr, ptr %a45
  %t85 = load i64, ptr %a19
  %t86 = icmp ne i64 %t85, 0
  %t87 = load %ax_arr, ptr %a18
  br i1 %t86, label %free88, label %cont89
free88:
  %t90 = extractvalue %ax_arr %t87, 0
  %t91 = extractvalue %ax_arr %t87, 1
  %t92 = mul i64 %t91, 1
  call void @ax_free(ptr %t90, i64 %t92)
  br label %cont89
cont89:
  %t93 = load i64, ptr %a2
  %t94 = icmp ne i64 %t93, 0
  %t95 = load %ax_arr, ptr %a1
  br i1 %t94, label %free96, label %cont97
free96:
  %t98 = extractvalue %ax_arr %t95, 0
  %t99 = extractvalue %ax_arr %t95, 1
  %t100 = mul i64 %t99, 1
  call void @ax_free(ptr %t98, i64 %t100)
  br label %cont97
cont97:
  %t101 = load i64, ptr %a5
  %t102 = icmp ne i64 %t101, 0
  %t103 = load %ax_arr, ptr %a4
  br i1 %t102, label %free104, label %cont105
free104:
  %t106 = extractvalue %ax_arr %t103, 0
  %t107 = extractvalue %ax_arr %t103, 1
  %t108 = mul i64 %t107, 1
  call void @ax_free(ptr %t106, i64 %t108)
  br label %cont105
cont105:
  %t109 = insertvalue %ax_arr %t84, i64 1, 2
  ret %ax_arr %t109
}

; jsx_Card  graph:439ae9a24f80e55e
define internal %ax_arr @ax_jsx_Card__seq(%ax_arr %p_p_title, %ax_arr %p_p_children) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a9 = alloca i64
  %a12 = alloca i64
  %a18 = alloca %ax_arr
  %a19 = alloca i64
  %a45 = alloca %ax_arr
  store %ax_arr %p_p_title, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_title, 2
  store i64 %t3, ptr %a2
  store %ax_arr %p_p_children, ptr %a4
  %t6 = extractvalue %ax_arr %p_p_children, 2
  store i64 %t6, ptr %a5
  %t7 = load %ax_arr, ptr %a1
  %t8 = extractvalue %ax_arr %t7, 1
  store i64 %t8, ptr %a9
  %t10 = load %ax_arr, ptr %a4
  %t11 = extractvalue %ax_arr %t10, 1
  store i64 %t11, ptr %a12
  %t13 = load %ax_arr, ptr %a1
  %t14 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t15 = insertvalue %ax_arr %t13, i64 %t14, 2
  %t16 = call %ax_arr @ax_escape__seq(%ax_arr %t15)
  %t17 = extractvalue %ax_arr %t16, 2
  store %ax_arr %t16, ptr %a18
  store i64 %t17, ptr %a19
  %t20 = insertvalue %ax_arr undef, ptr @.bytes.43, 0
  %t21 = insertvalue %ax_arr %t20, i64 29, 1
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = load %ax_arr, ptr %a18
  %t24 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t25 = insertvalue %ax_arr %t24, i64 6, 1
  %t26 = insertvalue %ax_arr %t25, i64 0, 2
  %t27 = load %ax_arr, ptr %a18
  %t28 = insertvalue %ax_arr undef, ptr @.bytes.45, 0
  %t29 = insertvalue %ax_arr %t28, i64 10, 1
  %t30 = insertvalue %ax_arr %t29, i64 0, 2
  %t31 = load %ax_arr, ptr %a4
  %t32 = load i64, ptr %a5
  store i64 0, ptr %a5
  %t33 = insertvalue %ax_arr undef, ptr @.bytes.46, 0
  %t34 = insertvalue %ax_arr %t33, i64 16, 1
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = extractvalue %ax_arr %t23, 1
  %t37 = extractvalue %ax_arr %t27, 1
  %t38 = extractvalue %ax_arr %t31, 1
  %t39 = add i64 29, %t36
  %t40 = add i64 %t39, 6
  %t41 = add i64 %t40, %t37
  %t42 = add i64 %t41, 10
  %t43 = add i64 %t42, %t38
  %t44 = add i64 %t43, 16
  br label %cat_fresh47
cat_fresh47:
  %t49 = icmp slt i64 %t44, 0
  %t50 = select i1 %t49, i64 0, i64 %t44
  %t51 = mul i64 %t50, 1
  %t52 = call ptr @ax_alloc(i64 %t51)
  %t53 = insertvalue %ax_arr undef, ptr %t52, 0
  %t54 = insertvalue %ax_arr %t53, i64 %t50, 1
  %t55 = insertvalue %ax_arr %t54, i64 1, 2
  %t56 = extractvalue %ax_arr %t55, 0
  %t57 = extractvalue %ax_arr %t22, 0
  %t58 = getelementptr inbounds i8, ptr %t56, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t58, ptr %t57, i64 29, i1 false)
  %t59 = add i64 0, 29
  %t60 = extractvalue %ax_arr %t23, 0
  %t61 = getelementptr inbounds i8, ptr %t56, i64 %t59
  call void @llvm.memcpy.p0.p0.i64(ptr %t61, ptr %t60, i64 %t36, i1 false)
  %t62 = add i64 %t59, %t36
  %t63 = extractvalue %ax_arr %t26, 0
  %t64 = getelementptr inbounds i8, ptr %t56, i64 %t62
  call void @llvm.memcpy.p0.p0.i64(ptr %t64, ptr %t63, i64 6, i1 false)
  %t65 = add i64 %t62, 6
  %t66 = extractvalue %ax_arr %t27, 0
  %t67 = getelementptr inbounds i8, ptr %t56, i64 %t65
  call void @llvm.memcpy.p0.p0.i64(ptr %t67, ptr %t66, i64 %t37, i1 false)
  %t68 = add i64 %t65, %t37
  %t69 = extractvalue %ax_arr %t30, 0
  %t70 = getelementptr inbounds i8, ptr %t56, i64 %t68
  call void @llvm.memcpy.p0.p0.i64(ptr %t70, ptr %t69, i64 10, i1 false)
  %t71 = add i64 %t68, 10
  %t72 = extractvalue %ax_arr %t31, 0
  %t73 = getelementptr inbounds i8, ptr %t56, i64 %t71
  call void @llvm.memcpy.p0.p0.i64(ptr %t73, ptr %t72, i64 %t38, i1 false)
  %t74 = add i64 %t71, %t38
  %t75 = icmp ne i64 %t32, 0
  br i1 %t75, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t31, 0
  %t79 = extractvalue %ax_arr %t31, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = extractvalue %ax_arr %t35, 0
  %t82 = getelementptr inbounds i8, ptr %t56, i64 %t74
  call void @llvm.memcpy.p0.p0.i64(ptr %t82, ptr %t81, i64 16, i1 false)
  %t83 = add i64 %t74, 16
  store %ax_arr %t55, ptr %a45
  br label %cat_join48
cat_join48:
  %t84 = load %ax_arr, ptr %a45
  %t85 = load i64, ptr %a19
  %t86 = icmp ne i64 %t85, 0
  %t87 = load %ax_arr, ptr %a18
  br i1 %t86, label %free88, label %cont89
free88:
  %t90 = extractvalue %ax_arr %t87, 0
  %t91 = extractvalue %ax_arr %t87, 1
  %t92 = mul i64 %t91, 1
  call void @ax_free(ptr %t90, i64 %t92)
  br label %cont89
cont89:
  %t93 = load i64, ptr %a2
  %t94 = icmp ne i64 %t93, 0
  %t95 = load %ax_arr, ptr %a1
  br i1 %t94, label %free96, label %cont97
free96:
  %t98 = extractvalue %ax_arr %t95, 0
  %t99 = extractvalue %ax_arr %t95, 1
  %t100 = mul i64 %t99, 1
  call void @ax_free(ptr %t98, i64 %t100)
  br label %cont97
cont97:
  %t101 = load i64, ptr %a5
  %t102 = icmp ne i64 %t101, 0
  %t103 = load %ax_arr, ptr %a4
  br i1 %t102, label %free104, label %cont105
free104:
  %t106 = extractvalue %ax_arr %t103, 0
  %t107 = extractvalue %ax_arr %t103, 1
  %t108 = mul i64 %t107, 1
  call void @ax_free(ptr %t106, i64 %t108)
  br label %cont105
cont105:
  %t109 = insertvalue %ax_arr %t84, i64 1, 2
  ret %ax_arr %t109
}

; jsx_Page  graph:90e464d3194ea3c0
define internal %ax_arr @ax_jsx_Page__par(%ax_arr %p_p_name, i64 %p_p_count, i1 %p_p_featured) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i1
  %a8 = alloca i64
  %a14 = alloca %ax_arr
  %a15 = alloca i64
  %a19 = alloca %ax_arr
  %a20 = alloca i64
  %a45 = alloca %ax_arr
  %a46 = alloca i64
  %a63 = alloca %ax_arr
  %a64 = alloca i64
  %a100 = alloca %ax_arr
  store %ax_arr %p_p_name, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_name, 2
  store i64 %t3, ptr %a2
  store i64 %p_p_count, ptr %a4
  store i1 %p_p_featured, ptr %a5
  %t6 = load %ax_arr, ptr %a1
  %t7 = extractvalue %ax_arr %t6, 1
  store i64 %t7, ptr %a8
  %t9 = load %ax_arr, ptr %a1
  %t10 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t11 = insertvalue %ax_arr %t9, i64 %t10, 2
  %t12 = call %ax_arr @ax_escape__par(%ax_arr %t11)
  %t13 = extractvalue %ax_arr %t12, 2
  store %ax_arr %t12, ptr %a14
  store i64 %t13, ptr %a15
  %t16 = load i64, ptr %a4
  %t17 = call %ax_arr @ax_utoa__par(i64 %t16)
  %t18 = extractvalue %ax_arr %t17, 2
  store %ax_arr %t17, ptr %a19
  store i64 %t18, ptr %a20
  %t21 = insertvalue %ax_arr undef, ptr @.bytes.47, 0
  %t22 = insertvalue %ax_arr %t21, i64 116, 1
  %t23 = insertvalue %ax_arr %t22, i64 0, 2
  %t24 = load %ax_arr, ptr %a14
  %t25 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t26 = insertvalue %ax_arr %t25, i64 6, 1
  %t27 = insertvalue %ax_arr %t26, i64 0, 2
  %t28 = load %ax_arr, ptr %a14
  %t29 = insertvalue %ax_arr undef, ptr @.bytes.48, 0
  %t30 = insertvalue %ax_arr %t29, i64 20, 1
  %t31 = insertvalue %ax_arr %t30, i64 0, 2
  %t32 = load %ax_arr, ptr %a14
  %t33 = insertvalue %ax_arr undef, ptr @.bytes.49, 0
  %t34 = insertvalue %ax_arr %t33, i64 20, 1
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = load %ax_arr, ptr %a19
  %t37 = insertvalue %ax_arr undef, ptr @.bytes.50, 0
  %t38 = insertvalue %ax_arr %t37, i64 12, 1
  %t39 = insertvalue %ax_arr %t38, i64 0, 2
  %t40 = load %ax_arr, ptr %a19
  %t41 = insertvalue %ax_arr undef, ptr @.bytes.51, 0
  %t42 = insertvalue %ax_arr %t41, i64 4, 1
  %t43 = insertvalue %ax_arr %t42, i64 0, 2
  %t44 = load i1, ptr %a5
  br i1 %t44, label %then47, label %else48
then47:
  %t50 = insertvalue %ax_arr undef, ptr @.bytes.52, 0
  %t51 = insertvalue %ax_arr %t50, i64 53, 1
  %t52 = insertvalue %ax_arr %t51, i64 0, 2
  store %ax_arr %t52, ptr %a45
  store i64 0, ptr %a46
  br label %join49
else48:
  %t53 = insertvalue %ax_arr undef, ptr @.bytes.53, 0
  %t54 = insertvalue %ax_arr %t53, i64 0, 1
  %t55 = insertvalue %ax_arr %t54, i64 0, 2
  store %ax_arr %t55, ptr %a45
  store i64 0, ptr %a46
  br label %join49
join49:
  %t56 = load %ax_arr, ptr %a45
  %t57 = load i64, ptr %a46
  %t58 = insertvalue %ax_arr undef, ptr @.bytes.54, 0
  %t59 = insertvalue %ax_arr %t58, i64 3, 1
  %t60 = insertvalue %ax_arr %t59, i64 0, 2
  %t61 = load i64, ptr %a4
  %t62 = icmp eq i64 %t61, 1
  br i1 %t62, label %then65, label %else66
then65:
  %t68 = insertvalue %ax_arr undef, ptr @.bytes.55, 0
  %t69 = insertvalue %ax_arr %t68, i64 8, 1
  %t70 = insertvalue %ax_arr %t69, i64 0, 2
  store %ax_arr %t70, ptr %a63
  store i64 0, ptr %a64
  br label %join67
else66:
  %t71 = insertvalue %ax_arr undef, ptr @.bytes.56, 0
  %t72 = insertvalue %ax_arr %t71, i64 10, 1
  %t73 = insertvalue %ax_arr %t72, i64 0, 2
  store %ax_arr %t73, ptr %a63
  store i64 0, ptr %a64
  br label %join67
join67:
  %t74 = load %ax_arr, ptr %a63
  %t75 = load i64, ptr %a64
  %t76 = insertvalue %ax_arr undef, ptr @.bytes.57, 0
  %t77 = insertvalue %ax_arr %t76, i64 136, 1
  %t78 = insertvalue %ax_arr %t77, i64 0, 2
  %t79 = extractvalue %ax_arr %t24, 1
  %t80 = extractvalue %ax_arr %t28, 1
  %t81 = extractvalue %ax_arr %t32, 1
  %t82 = extractvalue %ax_arr %t36, 1
  %t83 = extractvalue %ax_arr %t40, 1
  %t84 = extractvalue %ax_arr %t56, 1
  %t85 = extractvalue %ax_arr %t74, 1
  %t86 = add i64 116, %t79
  %t87 = add i64 %t86, 6
  %t88 = add i64 %t87, %t80
  %t89 = add i64 %t88, 20
  %t90 = add i64 %t89, %t81
  %t91 = add i64 %t90, 20
  %t92 = add i64 %t91, %t82
  %t93 = add i64 %t92, 12
  %t94 = add i64 %t93, %t83
  %t95 = add i64 %t94, 4
  %t96 = add i64 %t95, %t84
  %t97 = add i64 %t96, 3
  %t98 = add i64 %t97, %t85
  %t99 = add i64 %t98, 136
  br label %cat_fresh102
cat_fresh102:
  %t104 = icmp slt i64 %t99, 0
  %t105 = select i1 %t104, i64 0, i64 %t99
  %t106 = mul i64 %t105, 1
  %t107 = call ptr @ax_alloc(i64 %t106)
  %t108 = insertvalue %ax_arr undef, ptr %t107, 0
  %t109 = insertvalue %ax_arr %t108, i64 %t105, 1
  %t110 = insertvalue %ax_arr %t109, i64 1, 2
  %t111 = extractvalue %ax_arr %t110, 0
  %t112 = extractvalue %ax_arr %t23, 0
  %t113 = getelementptr inbounds i8, ptr %t111, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t113, ptr %t112, i64 116, i1 false)
  %t114 = add i64 0, 116
  %t115 = extractvalue %ax_arr %t24, 0
  %t116 = getelementptr inbounds i8, ptr %t111, i64 %t114
  call void @llvm.memcpy.p0.p0.i64(ptr %t116, ptr %t115, i64 %t79, i1 false)
  %t117 = add i64 %t114, %t79
  %t118 = extractvalue %ax_arr %t27, 0
  %t119 = getelementptr inbounds i8, ptr %t111, i64 %t117
  call void @llvm.memcpy.p0.p0.i64(ptr %t119, ptr %t118, i64 6, i1 false)
  %t120 = add i64 %t117, 6
  %t121 = extractvalue %ax_arr %t28, 0
  %t122 = getelementptr inbounds i8, ptr %t111, i64 %t120
  call void @llvm.memcpy.p0.p0.i64(ptr %t122, ptr %t121, i64 %t80, i1 false)
  %t123 = add i64 %t120, %t80
  %t124 = extractvalue %ax_arr %t31, 0
  %t125 = getelementptr inbounds i8, ptr %t111, i64 %t123
  call void @llvm.memcpy.p0.p0.i64(ptr %t125, ptr %t124, i64 20, i1 false)
  %t126 = add i64 %t123, 20
  %t127 = extractvalue %ax_arr %t32, 0
  %t128 = getelementptr inbounds i8, ptr %t111, i64 %t126
  call void @llvm.memcpy.p0.p0.i64(ptr %t128, ptr %t127, i64 %t81, i1 false)
  %t129 = add i64 %t126, %t81
  %t130 = extractvalue %ax_arr %t35, 0
  %t131 = getelementptr inbounds i8, ptr %t111, i64 %t129
  call void @llvm.memcpy.p0.p0.i64(ptr %t131, ptr %t130, i64 20, i1 false)
  %t132 = add i64 %t129, 20
  %t133 = extractvalue %ax_arr %t36, 0
  %t134 = getelementptr inbounds i8, ptr %t111, i64 %t132
  call void @llvm.memcpy.p0.p0.i64(ptr %t134, ptr %t133, i64 %t82, i1 false)
  %t135 = add i64 %t132, %t82
  %t136 = extractvalue %ax_arr %t39, 0
  %t137 = getelementptr inbounds i8, ptr %t111, i64 %t135
  call void @llvm.memcpy.p0.p0.i64(ptr %t137, ptr %t136, i64 12, i1 false)
  %t138 = add i64 %t135, 12
  %t139 = extractvalue %ax_arr %t40, 0
  %t140 = getelementptr inbounds i8, ptr %t111, i64 %t138
  call void @llvm.memcpy.p0.p0.i64(ptr %t140, ptr %t139, i64 %t83, i1 false)
  %t141 = add i64 %t138, %t83
  %t142 = extractvalue %ax_arr %t43, 0
  %t143 = getelementptr inbounds i8, ptr %t111, i64 %t141
  call void @llvm.memcpy.p0.p0.i64(ptr %t143, ptr %t142, i64 4, i1 false)
  %t144 = add i64 %t141, 4
  %t145 = extractvalue %ax_arr %t56, 0
  %t146 = getelementptr inbounds i8, ptr %t111, i64 %t144
  call void @llvm.memcpy.p0.p0.i64(ptr %t146, ptr %t145, i64 %t84, i1 false)
  %t147 = add i64 %t144, %t84
  %t148 = icmp ne i64 %t57, 0
  br i1 %t148, label %free149, label %cont150
free149:
  %t151 = extractvalue %ax_arr %t56, 0
  %t152 = extractvalue %ax_arr %t56, 1
  %t153 = mul i64 %t152, 1
  call void @ax_free(ptr %t151, i64 %t153)
  br label %cont150
cont150:
  %t154 = extractvalue %ax_arr %t60, 0
  %t155 = getelementptr inbounds i8, ptr %t111, i64 %t147
  call void @llvm.memcpy.p0.p0.i64(ptr %t155, ptr %t154, i64 3, i1 false)
  %t156 = add i64 %t147, 3
  %t157 = extractvalue %ax_arr %t74, 0
  %t158 = getelementptr inbounds i8, ptr %t111, i64 %t156
  call void @llvm.memcpy.p0.p0.i64(ptr %t158, ptr %t157, i64 %t85, i1 false)
  %t159 = add i64 %t156, %t85
  %t160 = icmp ne i64 %t75, 0
  br i1 %t160, label %free161, label %cont162
free161:
  %t163 = extractvalue %ax_arr %t74, 0
  %t164 = extractvalue %ax_arr %t74, 1
  %t165 = mul i64 %t164, 1
  call void @ax_free(ptr %t163, i64 %t165)
  br label %cont162
cont162:
  %t166 = extractvalue %ax_arr %t78, 0
  %t167 = getelementptr inbounds i8, ptr %t111, i64 %t159
  call void @llvm.memcpy.p0.p0.i64(ptr %t167, ptr %t166, i64 136, i1 false)
  %t168 = add i64 %t159, 136
  store %ax_arr %t110, ptr %a100
  br label %cat_join103
cat_join103:
  %t169 = load %ax_arr, ptr %a100
  %t170 = load i64, ptr %a20
  %t171 = icmp ne i64 %t170, 0
  %t172 = load %ax_arr, ptr %a19
  br i1 %t171, label %free173, label %cont174
free173:
  %t175 = extractvalue %ax_arr %t172, 0
  %t176 = extractvalue %ax_arr %t172, 1
  %t177 = mul i64 %t176, 1
  call void @ax_free(ptr %t175, i64 %t177)
  br label %cont174
cont174:
  %t178 = load i64, ptr %a15
  %t179 = icmp ne i64 %t178, 0
  %t180 = load %ax_arr, ptr %a14
  br i1 %t179, label %free181, label %cont182
free181:
  %t183 = extractvalue %ax_arr %t180, 0
  %t184 = extractvalue %ax_arr %t180, 1
  %t185 = mul i64 %t184, 1
  call void @ax_free(ptr %t183, i64 %t185)
  br label %cont182
cont182:
  %t186 = load i64, ptr %a2
  %t187 = icmp ne i64 %t186, 0
  %t188 = load %ax_arr, ptr %a1
  br i1 %t187, label %free189, label %cont190
free189:
  %t191 = extractvalue %ax_arr %t188, 0
  %t192 = extractvalue %ax_arr %t188, 1
  %t193 = mul i64 %t192, 1
  call void @ax_free(ptr %t191, i64 %t193)
  br label %cont190
cont190:
  %t194 = insertvalue %ax_arr %t169, i64 1, 2
  ret %ax_arr %t194
}

; jsx_Page  graph:90e464d3194ea3c0
define internal %ax_arr @ax_jsx_Page__seq(%ax_arr %p_p_name, i64 %p_p_count, i1 %p_p_featured) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a4 = alloca i64
  %a5 = alloca i1
  %a8 = alloca i64
  %a14 = alloca %ax_arr
  %a15 = alloca i64
  %a19 = alloca %ax_arr
  %a20 = alloca i64
  %a45 = alloca %ax_arr
  %a46 = alloca i64
  %a63 = alloca %ax_arr
  %a64 = alloca i64
  %a100 = alloca %ax_arr
  store %ax_arr %p_p_name, ptr %a1
  %t3 = extractvalue %ax_arr %p_p_name, 2
  store i64 %t3, ptr %a2
  store i64 %p_p_count, ptr %a4
  store i1 %p_p_featured, ptr %a5
  %t6 = load %ax_arr, ptr %a1
  %t7 = extractvalue %ax_arr %t6, 1
  store i64 %t7, ptr %a8
  %t9 = load %ax_arr, ptr %a1
  %t10 = load i64, ptr %a2
  store i64 0, ptr %a2
  %t11 = insertvalue %ax_arr %t9, i64 %t10, 2
  %t12 = call %ax_arr @ax_escape__seq(%ax_arr %t11)
  %t13 = extractvalue %ax_arr %t12, 2
  store %ax_arr %t12, ptr %a14
  store i64 %t13, ptr %a15
  %t16 = load i64, ptr %a4
  %t17 = call %ax_arr @ax_utoa__seq(i64 %t16)
  %t18 = extractvalue %ax_arr %t17, 2
  store %ax_arr %t17, ptr %a19
  store i64 %t18, ptr %a20
  %t21 = insertvalue %ax_arr undef, ptr @.bytes.47, 0
  %t22 = insertvalue %ax_arr %t21, i64 116, 1
  %t23 = insertvalue %ax_arr %t22, i64 0, 2
  %t24 = load %ax_arr, ptr %a14
  %t25 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t26 = insertvalue %ax_arr %t25, i64 6, 1
  %t27 = insertvalue %ax_arr %t26, i64 0, 2
  %t28 = load %ax_arr, ptr %a14
  %t29 = insertvalue %ax_arr undef, ptr @.bytes.48, 0
  %t30 = insertvalue %ax_arr %t29, i64 20, 1
  %t31 = insertvalue %ax_arr %t30, i64 0, 2
  %t32 = load %ax_arr, ptr %a14
  %t33 = insertvalue %ax_arr undef, ptr @.bytes.49, 0
  %t34 = insertvalue %ax_arr %t33, i64 20, 1
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = load %ax_arr, ptr %a19
  %t37 = insertvalue %ax_arr undef, ptr @.bytes.50, 0
  %t38 = insertvalue %ax_arr %t37, i64 12, 1
  %t39 = insertvalue %ax_arr %t38, i64 0, 2
  %t40 = load %ax_arr, ptr %a19
  %t41 = insertvalue %ax_arr undef, ptr @.bytes.51, 0
  %t42 = insertvalue %ax_arr %t41, i64 4, 1
  %t43 = insertvalue %ax_arr %t42, i64 0, 2
  %t44 = load i1, ptr %a5
  br i1 %t44, label %then47, label %else48
then47:
  %t50 = insertvalue %ax_arr undef, ptr @.bytes.52, 0
  %t51 = insertvalue %ax_arr %t50, i64 53, 1
  %t52 = insertvalue %ax_arr %t51, i64 0, 2
  store %ax_arr %t52, ptr %a45
  store i64 0, ptr %a46
  br label %join49
else48:
  %t53 = insertvalue %ax_arr undef, ptr @.bytes.53, 0
  %t54 = insertvalue %ax_arr %t53, i64 0, 1
  %t55 = insertvalue %ax_arr %t54, i64 0, 2
  store %ax_arr %t55, ptr %a45
  store i64 0, ptr %a46
  br label %join49
join49:
  %t56 = load %ax_arr, ptr %a45
  %t57 = load i64, ptr %a46
  %t58 = insertvalue %ax_arr undef, ptr @.bytes.54, 0
  %t59 = insertvalue %ax_arr %t58, i64 3, 1
  %t60 = insertvalue %ax_arr %t59, i64 0, 2
  %t61 = load i64, ptr %a4
  %t62 = icmp eq i64 %t61, 1
  br i1 %t62, label %then65, label %else66
then65:
  %t68 = insertvalue %ax_arr undef, ptr @.bytes.55, 0
  %t69 = insertvalue %ax_arr %t68, i64 8, 1
  %t70 = insertvalue %ax_arr %t69, i64 0, 2
  store %ax_arr %t70, ptr %a63
  store i64 0, ptr %a64
  br label %join67
else66:
  %t71 = insertvalue %ax_arr undef, ptr @.bytes.56, 0
  %t72 = insertvalue %ax_arr %t71, i64 10, 1
  %t73 = insertvalue %ax_arr %t72, i64 0, 2
  store %ax_arr %t73, ptr %a63
  store i64 0, ptr %a64
  br label %join67
join67:
  %t74 = load %ax_arr, ptr %a63
  %t75 = load i64, ptr %a64
  %t76 = insertvalue %ax_arr undef, ptr @.bytes.57, 0
  %t77 = insertvalue %ax_arr %t76, i64 136, 1
  %t78 = insertvalue %ax_arr %t77, i64 0, 2
  %t79 = extractvalue %ax_arr %t24, 1
  %t80 = extractvalue %ax_arr %t28, 1
  %t81 = extractvalue %ax_arr %t32, 1
  %t82 = extractvalue %ax_arr %t36, 1
  %t83 = extractvalue %ax_arr %t40, 1
  %t84 = extractvalue %ax_arr %t56, 1
  %t85 = extractvalue %ax_arr %t74, 1
  %t86 = add i64 116, %t79
  %t87 = add i64 %t86, 6
  %t88 = add i64 %t87, %t80
  %t89 = add i64 %t88, 20
  %t90 = add i64 %t89, %t81
  %t91 = add i64 %t90, 20
  %t92 = add i64 %t91, %t82
  %t93 = add i64 %t92, 12
  %t94 = add i64 %t93, %t83
  %t95 = add i64 %t94, 4
  %t96 = add i64 %t95, %t84
  %t97 = add i64 %t96, 3
  %t98 = add i64 %t97, %t85
  %t99 = add i64 %t98, 136
  br label %cat_fresh102
cat_fresh102:
  %t104 = icmp slt i64 %t99, 0
  %t105 = select i1 %t104, i64 0, i64 %t99
  %t106 = mul i64 %t105, 1
  %t107 = call ptr @ax_alloc(i64 %t106)
  %t108 = insertvalue %ax_arr undef, ptr %t107, 0
  %t109 = insertvalue %ax_arr %t108, i64 %t105, 1
  %t110 = insertvalue %ax_arr %t109, i64 1, 2
  %t111 = extractvalue %ax_arr %t110, 0
  %t112 = extractvalue %ax_arr %t23, 0
  %t113 = getelementptr inbounds i8, ptr %t111, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t113, ptr %t112, i64 116, i1 false)
  %t114 = add i64 0, 116
  %t115 = extractvalue %ax_arr %t24, 0
  %t116 = getelementptr inbounds i8, ptr %t111, i64 %t114
  call void @llvm.memcpy.p0.p0.i64(ptr %t116, ptr %t115, i64 %t79, i1 false)
  %t117 = add i64 %t114, %t79
  %t118 = extractvalue %ax_arr %t27, 0
  %t119 = getelementptr inbounds i8, ptr %t111, i64 %t117
  call void @llvm.memcpy.p0.p0.i64(ptr %t119, ptr %t118, i64 6, i1 false)
  %t120 = add i64 %t117, 6
  %t121 = extractvalue %ax_arr %t28, 0
  %t122 = getelementptr inbounds i8, ptr %t111, i64 %t120
  call void @llvm.memcpy.p0.p0.i64(ptr %t122, ptr %t121, i64 %t80, i1 false)
  %t123 = add i64 %t120, %t80
  %t124 = extractvalue %ax_arr %t31, 0
  %t125 = getelementptr inbounds i8, ptr %t111, i64 %t123
  call void @llvm.memcpy.p0.p0.i64(ptr %t125, ptr %t124, i64 20, i1 false)
  %t126 = add i64 %t123, 20
  %t127 = extractvalue %ax_arr %t32, 0
  %t128 = getelementptr inbounds i8, ptr %t111, i64 %t126
  call void @llvm.memcpy.p0.p0.i64(ptr %t128, ptr %t127, i64 %t81, i1 false)
  %t129 = add i64 %t126, %t81
  %t130 = extractvalue %ax_arr %t35, 0
  %t131 = getelementptr inbounds i8, ptr %t111, i64 %t129
  call void @llvm.memcpy.p0.p0.i64(ptr %t131, ptr %t130, i64 20, i1 false)
  %t132 = add i64 %t129, 20
  %t133 = extractvalue %ax_arr %t36, 0
  %t134 = getelementptr inbounds i8, ptr %t111, i64 %t132
  call void @llvm.memcpy.p0.p0.i64(ptr %t134, ptr %t133, i64 %t82, i1 false)
  %t135 = add i64 %t132, %t82
  %t136 = extractvalue %ax_arr %t39, 0
  %t137 = getelementptr inbounds i8, ptr %t111, i64 %t135
  call void @llvm.memcpy.p0.p0.i64(ptr %t137, ptr %t136, i64 12, i1 false)
  %t138 = add i64 %t135, 12
  %t139 = extractvalue %ax_arr %t40, 0
  %t140 = getelementptr inbounds i8, ptr %t111, i64 %t138
  call void @llvm.memcpy.p0.p0.i64(ptr %t140, ptr %t139, i64 %t83, i1 false)
  %t141 = add i64 %t138, %t83
  %t142 = extractvalue %ax_arr %t43, 0
  %t143 = getelementptr inbounds i8, ptr %t111, i64 %t141
  call void @llvm.memcpy.p0.p0.i64(ptr %t143, ptr %t142, i64 4, i1 false)
  %t144 = add i64 %t141, 4
  %t145 = extractvalue %ax_arr %t56, 0
  %t146 = getelementptr inbounds i8, ptr %t111, i64 %t144
  call void @llvm.memcpy.p0.p0.i64(ptr %t146, ptr %t145, i64 %t84, i1 false)
  %t147 = add i64 %t144, %t84
  %t148 = icmp ne i64 %t57, 0
  br i1 %t148, label %free149, label %cont150
free149:
  %t151 = extractvalue %ax_arr %t56, 0
  %t152 = extractvalue %ax_arr %t56, 1
  %t153 = mul i64 %t152, 1
  call void @ax_free(ptr %t151, i64 %t153)
  br label %cont150
cont150:
  %t154 = extractvalue %ax_arr %t60, 0
  %t155 = getelementptr inbounds i8, ptr %t111, i64 %t147
  call void @llvm.memcpy.p0.p0.i64(ptr %t155, ptr %t154, i64 3, i1 false)
  %t156 = add i64 %t147, 3
  %t157 = extractvalue %ax_arr %t74, 0
  %t158 = getelementptr inbounds i8, ptr %t111, i64 %t156
  call void @llvm.memcpy.p0.p0.i64(ptr %t158, ptr %t157, i64 %t85, i1 false)
  %t159 = add i64 %t156, %t85
  %t160 = icmp ne i64 %t75, 0
  br i1 %t160, label %free161, label %cont162
free161:
  %t163 = extractvalue %ax_arr %t74, 0
  %t164 = extractvalue %ax_arr %t74, 1
  %t165 = mul i64 %t164, 1
  call void @ax_free(ptr %t163, i64 %t165)
  br label %cont162
cont162:
  %t166 = extractvalue %ax_arr %t78, 0
  %t167 = getelementptr inbounds i8, ptr %t111, i64 %t159
  call void @llvm.memcpy.p0.p0.i64(ptr %t167, ptr %t166, i64 136, i1 false)
  %t168 = add i64 %t159, 136
  store %ax_arr %t110, ptr %a100
  br label %cat_join103
cat_join103:
  %t169 = load %ax_arr, ptr %a100
  %t170 = load i64, ptr %a20
  %t171 = icmp ne i64 %t170, 0
  %t172 = load %ax_arr, ptr %a19
  br i1 %t171, label %free173, label %cont174
free173:
  %t175 = extractvalue %ax_arr %t172, 0
  %t176 = extractvalue %ax_arr %t172, 1
  %t177 = mul i64 %t176, 1
  call void @ax_free(ptr %t175, i64 %t177)
  br label %cont174
cont174:
  %t178 = load i64, ptr %a15
  %t179 = icmp ne i64 %t178, 0
  %t180 = load %ax_arr, ptr %a14
  br i1 %t179, label %free181, label %cont182
free181:
  %t183 = extractvalue %ax_arr %t180, 0
  %t184 = extractvalue %ax_arr %t180, 1
  %t185 = mul i64 %t184, 1
  call void @ax_free(ptr %t183, i64 %t185)
  br label %cont182
cont182:
  %t186 = load i64, ptr %a2
  %t187 = icmp ne i64 %t186, 0
  %t188 = load %ax_arr, ptr %a1
  br i1 %t187, label %free189, label %cont190
free189:
  %t191 = extractvalue %ax_arr %t188, 0
  %t192 = extractvalue %ax_arr %t188, 1
  %t193 = mul i64 %t192, 1
  call void @ax_free(ptr %t191, i64 %t193)
  br label %cont190
cont190:
  %t194 = insertvalue %ax_arr %t169, i64 1, 2
  ret %ax_arr %t194
}

; page  graph:0c9837ebe557edd7
define internal %ax_arr @ax_page__par(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a17 = alloca %ax_arr
  %a18 = alloca i64
  %a20 = alloca i64
  %a24 = alloca i1
  %a27 = alloca i64
  %a33 = alloca %ax_arr
  %a34 = alloca i64
  %a38 = alloca %ax_arr
  %a39 = alloca i64
  %a67 = alloca %ax_arr
  %a68 = alloca i64
  %a85 = alloca %ax_arr
  %a86 = alloca i64
  %a123 = alloca %ax_arr
  store i64 %p_n, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = icmp eq i64 %t2, 13
  br i1 %t3, label %then6, label %else7
then6:
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.58, 0
  %t10 = insertvalue %ax_arr %t9, i64 42, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  store %ax_arr %t11, ptr %a4
  store i64 0, ptr %a5
  br label %join8
else7:
  %t12 = insertvalue %ax_arr undef, ptr @.bytes.59, 0
  %t13 = insertvalue %ax_arr %t12, i64 33, 1
  %t14 = insertvalue %ax_arr %t13, i64 0, 2
  store %ax_arr %t14, ptr %a4
  store i64 0, ptr %a5
  br label %join8
join8:
  %t15 = load %ax_arr, ptr %a4
  %t16 = load i64, ptr %a5
  store %ax_arr %t15, ptr %a17
  store i64 %t16, ptr %a18
  %t19 = load i64, ptr %a1
  store i64 %t19, ptr %a20
  %t21 = load i64, ptr %a1
  %t22 = srem i64 %t21, 2
  %t23 = icmp eq i64 %t22, 0
  store i1 %t23, ptr %a24
  %t25 = load %ax_arr, ptr %a17
  %t26 = extractvalue %ax_arr %t25, 1
  store i64 %t26, ptr %a27
  %t28 = load %ax_arr, ptr %a17
  %t29 = load i64, ptr %a18
  store i64 0, ptr %a18
  %t30 = insertvalue %ax_arr %t28, i64 %t29, 2
  %t31 = call %ax_arr @ax_escape__par(%ax_arr %t30)
  %t32 = extractvalue %ax_arr %t31, 2
  store %ax_arr %t31, ptr %a33
  store i64 %t32, ptr %a34
  %t35 = load i64, ptr %a20
  %t36 = call %ax_arr @ax_utoa__par(i64 %t35)
  %t37 = extractvalue %ax_arr %t36, 2
  store %ax_arr %t36, ptr %a38
  store i64 %t37, ptr %a39
  %t40 = insertvalue %ax_arr undef, ptr @.bytes.60, 0
  %t41 = insertvalue %ax_arr %t40, i64 15, 1
  %t42 = insertvalue %ax_arr %t41, i64 0, 2
  %t43 = insertvalue %ax_arr undef, ptr @.bytes.47, 0
  %t44 = insertvalue %ax_arr %t43, i64 116, 1
  %t45 = insertvalue %ax_arr %t44, i64 0, 2
  %t46 = load %ax_arr, ptr %a33
  %t47 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t48 = insertvalue %ax_arr %t47, i64 6, 1
  %t49 = insertvalue %ax_arr %t48, i64 0, 2
  %t50 = load %ax_arr, ptr %a33
  %t51 = insertvalue %ax_arr undef, ptr @.bytes.48, 0
  %t52 = insertvalue %ax_arr %t51, i64 20, 1
  %t53 = insertvalue %ax_arr %t52, i64 0, 2
  %t54 = load %ax_arr, ptr %a33
  %t55 = insertvalue %ax_arr undef, ptr @.bytes.49, 0
  %t56 = insertvalue %ax_arr %t55, i64 20, 1
  %t57 = insertvalue %ax_arr %t56, i64 0, 2
  %t58 = load %ax_arr, ptr %a38
  %t59 = insertvalue %ax_arr undef, ptr @.bytes.50, 0
  %t60 = insertvalue %ax_arr %t59, i64 12, 1
  %t61 = insertvalue %ax_arr %t60, i64 0, 2
  %t62 = load %ax_arr, ptr %a38
  %t63 = insertvalue %ax_arr undef, ptr @.bytes.51, 0
  %t64 = insertvalue %ax_arr %t63, i64 4, 1
  %t65 = insertvalue %ax_arr %t64, i64 0, 2
  %t66 = load i1, ptr %a24
  br i1 %t66, label %then69, label %else70
then69:
  %t72 = insertvalue %ax_arr undef, ptr @.bytes.52, 0
  %t73 = insertvalue %ax_arr %t72, i64 53, 1
  %t74 = insertvalue %ax_arr %t73, i64 0, 2
  store %ax_arr %t74, ptr %a67
  store i64 0, ptr %a68
  br label %join71
else70:
  %t75 = insertvalue %ax_arr undef, ptr @.bytes.53, 0
  %t76 = insertvalue %ax_arr %t75, i64 0, 1
  %t77 = insertvalue %ax_arr %t76, i64 0, 2
  store %ax_arr %t77, ptr %a67
  store i64 0, ptr %a68
  br label %join71
join71:
  %t78 = load %ax_arr, ptr %a67
  %t79 = load i64, ptr %a68
  %t80 = insertvalue %ax_arr undef, ptr @.bytes.54, 0
  %t81 = insertvalue %ax_arr %t80, i64 3, 1
  %t82 = insertvalue %ax_arr %t81, i64 0, 2
  %t83 = load i64, ptr %a20
  %t84 = icmp eq i64 %t83, 1
  br i1 %t84, label %then87, label %else88
then87:
  %t90 = insertvalue %ax_arr undef, ptr @.bytes.55, 0
  %t91 = insertvalue %ax_arr %t90, i64 8, 1
  %t92 = insertvalue %ax_arr %t91, i64 0, 2
  store %ax_arr %t92, ptr %a85
  store i64 0, ptr %a86
  br label %join89
else88:
  %t93 = insertvalue %ax_arr undef, ptr @.bytes.56, 0
  %t94 = insertvalue %ax_arr %t93, i64 10, 1
  %t95 = insertvalue %ax_arr %t94, i64 0, 2
  store %ax_arr %t95, ptr %a85
  store i64 0, ptr %a86
  br label %join89
join89:
  %t96 = load %ax_arr, ptr %a85
  %t97 = load i64, ptr %a86
  %t98 = insertvalue %ax_arr undef, ptr @.bytes.57, 0
  %t99 = insertvalue %ax_arr %t98, i64 136, 1
  %t100 = insertvalue %ax_arr %t99, i64 0, 2
  %t101 = extractvalue %ax_arr %t46, 1
  %t102 = extractvalue %ax_arr %t50, 1
  %t103 = extractvalue %ax_arr %t54, 1
  %t104 = extractvalue %ax_arr %t58, 1
  %t105 = extractvalue %ax_arr %t62, 1
  %t106 = extractvalue %ax_arr %t78, 1
  %t107 = extractvalue %ax_arr %t96, 1
  %t108 = add i64 15, 116
  %t109 = add i64 %t108, %t101
  %t110 = add i64 %t109, 6
  %t111 = add i64 %t110, %t102
  %t112 = add i64 %t111, 20
  %t113 = add i64 %t112, %t103
  %t114 = add i64 %t113, 20
  %t115 = add i64 %t114, %t104
  %t116 = add i64 %t115, 12
  %t117 = add i64 %t116, %t105
  %t118 = add i64 %t117, 4
  %t119 = add i64 %t118, %t106
  %t120 = add i64 %t119, 3
  %t121 = add i64 %t120, %t107
  %t122 = add i64 %t121, 136
  br label %cat_fresh125
cat_fresh125:
  %t127 = icmp slt i64 %t122, 0
  %t128 = select i1 %t127, i64 0, i64 %t122
  %t129 = mul i64 %t128, 1
  %t130 = call ptr @ax_alloc(i64 %t129)
  %t131 = insertvalue %ax_arr undef, ptr %t130, 0
  %t132 = insertvalue %ax_arr %t131, i64 %t128, 1
  %t133 = insertvalue %ax_arr %t132, i64 1, 2
  %t134 = extractvalue %ax_arr %t133, 0
  %t135 = extractvalue %ax_arr %t42, 0
  %t136 = getelementptr inbounds i8, ptr %t134, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t136, ptr %t135, i64 15, i1 false)
  %t137 = add i64 0, 15
  %t138 = extractvalue %ax_arr %t45, 0
  %t139 = getelementptr inbounds i8, ptr %t134, i64 %t137
  call void @llvm.memcpy.p0.p0.i64(ptr %t139, ptr %t138, i64 116, i1 false)
  %t140 = add i64 %t137, 116
  %t141 = extractvalue %ax_arr %t46, 0
  %t142 = getelementptr inbounds i8, ptr %t134, i64 %t140
  call void @llvm.memcpy.p0.p0.i64(ptr %t142, ptr %t141, i64 %t101, i1 false)
  %t143 = add i64 %t140, %t101
  %t144 = extractvalue %ax_arr %t49, 0
  %t145 = getelementptr inbounds i8, ptr %t134, i64 %t143
  call void @llvm.memcpy.p0.p0.i64(ptr %t145, ptr %t144, i64 6, i1 false)
  %t146 = add i64 %t143, 6
  %t147 = extractvalue %ax_arr %t50, 0
  %t148 = getelementptr inbounds i8, ptr %t134, i64 %t146
  call void @llvm.memcpy.p0.p0.i64(ptr %t148, ptr %t147, i64 %t102, i1 false)
  %t149 = add i64 %t146, %t102
  %t150 = extractvalue %ax_arr %t53, 0
  %t151 = getelementptr inbounds i8, ptr %t134, i64 %t149
  call void @llvm.memcpy.p0.p0.i64(ptr %t151, ptr %t150, i64 20, i1 false)
  %t152 = add i64 %t149, 20
  %t153 = extractvalue %ax_arr %t54, 0
  %t154 = getelementptr inbounds i8, ptr %t134, i64 %t152
  call void @llvm.memcpy.p0.p0.i64(ptr %t154, ptr %t153, i64 %t103, i1 false)
  %t155 = add i64 %t152, %t103
  %t156 = extractvalue %ax_arr %t57, 0
  %t157 = getelementptr inbounds i8, ptr %t134, i64 %t155
  call void @llvm.memcpy.p0.p0.i64(ptr %t157, ptr %t156, i64 20, i1 false)
  %t158 = add i64 %t155, 20
  %t159 = extractvalue %ax_arr %t58, 0
  %t160 = getelementptr inbounds i8, ptr %t134, i64 %t158
  call void @llvm.memcpy.p0.p0.i64(ptr %t160, ptr %t159, i64 %t104, i1 false)
  %t161 = add i64 %t158, %t104
  %t162 = extractvalue %ax_arr %t61, 0
  %t163 = getelementptr inbounds i8, ptr %t134, i64 %t161
  call void @llvm.memcpy.p0.p0.i64(ptr %t163, ptr %t162, i64 12, i1 false)
  %t164 = add i64 %t161, 12
  %t165 = extractvalue %ax_arr %t62, 0
  %t166 = getelementptr inbounds i8, ptr %t134, i64 %t164
  call void @llvm.memcpy.p0.p0.i64(ptr %t166, ptr %t165, i64 %t105, i1 false)
  %t167 = add i64 %t164, %t105
  %t168 = extractvalue %ax_arr %t65, 0
  %t169 = getelementptr inbounds i8, ptr %t134, i64 %t167
  call void @llvm.memcpy.p0.p0.i64(ptr %t169, ptr %t168, i64 4, i1 false)
  %t170 = add i64 %t167, 4
  %t171 = extractvalue %ax_arr %t78, 0
  %t172 = getelementptr inbounds i8, ptr %t134, i64 %t170
  call void @llvm.memcpy.p0.p0.i64(ptr %t172, ptr %t171, i64 %t106, i1 false)
  %t173 = add i64 %t170, %t106
  %t174 = icmp ne i64 %t79, 0
  br i1 %t174, label %free175, label %cont176
free175:
  %t177 = extractvalue %ax_arr %t78, 0
  %t178 = extractvalue %ax_arr %t78, 1
  %t179 = mul i64 %t178, 1
  call void @ax_free(ptr %t177, i64 %t179)
  br label %cont176
cont176:
  %t180 = extractvalue %ax_arr %t82, 0
  %t181 = getelementptr inbounds i8, ptr %t134, i64 %t173
  call void @llvm.memcpy.p0.p0.i64(ptr %t181, ptr %t180, i64 3, i1 false)
  %t182 = add i64 %t173, 3
  %t183 = extractvalue %ax_arr %t96, 0
  %t184 = getelementptr inbounds i8, ptr %t134, i64 %t182
  call void @llvm.memcpy.p0.p0.i64(ptr %t184, ptr %t183, i64 %t107, i1 false)
  %t185 = add i64 %t182, %t107
  %t186 = icmp ne i64 %t97, 0
  br i1 %t186, label %free187, label %cont188
free187:
  %t189 = extractvalue %ax_arr %t96, 0
  %t190 = extractvalue %ax_arr %t96, 1
  %t191 = mul i64 %t190, 1
  call void @ax_free(ptr %t189, i64 %t191)
  br label %cont188
cont188:
  %t192 = extractvalue %ax_arr %t100, 0
  %t193 = getelementptr inbounds i8, ptr %t134, i64 %t185
  call void @llvm.memcpy.p0.p0.i64(ptr %t193, ptr %t192, i64 136, i1 false)
  %t194 = add i64 %t185, 136
  store %ax_arr %t133, ptr %a123
  br label %cat_join126
cat_join126:
  %t195 = load %ax_arr, ptr %a123
  %t196 = load i64, ptr %a39
  %t197 = icmp ne i64 %t196, 0
  %t198 = load %ax_arr, ptr %a38
  br i1 %t197, label %free199, label %cont200
free199:
  %t201 = extractvalue %ax_arr %t198, 0
  %t202 = extractvalue %ax_arr %t198, 1
  %t203 = mul i64 %t202, 1
  call void @ax_free(ptr %t201, i64 %t203)
  br label %cont200
cont200:
  %t204 = load i64, ptr %a34
  %t205 = icmp ne i64 %t204, 0
  %t206 = load %ax_arr, ptr %a33
  br i1 %t205, label %free207, label %cont208
free207:
  %t209 = extractvalue %ax_arr %t206, 0
  %t210 = extractvalue %ax_arr %t206, 1
  %t211 = mul i64 %t210, 1
  call void @ax_free(ptr %t209, i64 %t211)
  br label %cont208
cont208:
  %t212 = load i64, ptr %a18
  %t213 = icmp ne i64 %t212, 0
  %t214 = load %ax_arr, ptr %a17
  br i1 %t213, label %free215, label %cont216
free215:
  %t217 = extractvalue %ax_arr %t214, 0
  %t218 = extractvalue %ax_arr %t214, 1
  %t219 = mul i64 %t218, 1
  call void @ax_free(ptr %t217, i64 %t219)
  br label %cont216
cont216:
  %t220 = insertvalue %ax_arr %t195, i64 1, 2
  ret %ax_arr %t220
}

; page  graph:0c9837ebe557edd7
define internal %ax_arr @ax_page__seq(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a4 = alloca %ax_arr
  %a5 = alloca i64
  %a17 = alloca %ax_arr
  %a18 = alloca i64
  %a20 = alloca i64
  %a24 = alloca i1
  %a27 = alloca i64
  %a33 = alloca %ax_arr
  %a34 = alloca i64
  %a38 = alloca %ax_arr
  %a39 = alloca i64
  %a67 = alloca %ax_arr
  %a68 = alloca i64
  %a85 = alloca %ax_arr
  %a86 = alloca i64
  %a123 = alloca %ax_arr
  store i64 %p_n, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = icmp eq i64 %t2, 13
  br i1 %t3, label %then6, label %else7
then6:
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.58, 0
  %t10 = insertvalue %ax_arr %t9, i64 42, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  store %ax_arr %t11, ptr %a4
  store i64 0, ptr %a5
  br label %join8
else7:
  %t12 = insertvalue %ax_arr undef, ptr @.bytes.59, 0
  %t13 = insertvalue %ax_arr %t12, i64 33, 1
  %t14 = insertvalue %ax_arr %t13, i64 0, 2
  store %ax_arr %t14, ptr %a4
  store i64 0, ptr %a5
  br label %join8
join8:
  %t15 = load %ax_arr, ptr %a4
  %t16 = load i64, ptr %a5
  store %ax_arr %t15, ptr %a17
  store i64 %t16, ptr %a18
  %t19 = load i64, ptr %a1
  store i64 %t19, ptr %a20
  %t21 = load i64, ptr %a1
  %t22 = srem i64 %t21, 2
  %t23 = icmp eq i64 %t22, 0
  store i1 %t23, ptr %a24
  %t25 = load %ax_arr, ptr %a17
  %t26 = extractvalue %ax_arr %t25, 1
  store i64 %t26, ptr %a27
  %t28 = load %ax_arr, ptr %a17
  %t29 = load i64, ptr %a18
  store i64 0, ptr %a18
  %t30 = insertvalue %ax_arr %t28, i64 %t29, 2
  %t31 = call %ax_arr @ax_escape__seq(%ax_arr %t30)
  %t32 = extractvalue %ax_arr %t31, 2
  store %ax_arr %t31, ptr %a33
  store i64 %t32, ptr %a34
  %t35 = load i64, ptr %a20
  %t36 = call %ax_arr @ax_utoa__seq(i64 %t35)
  %t37 = extractvalue %ax_arr %t36, 2
  store %ax_arr %t36, ptr %a38
  store i64 %t37, ptr %a39
  %t40 = insertvalue %ax_arr undef, ptr @.bytes.60, 0
  %t41 = insertvalue %ax_arr %t40, i64 15, 1
  %t42 = insertvalue %ax_arr %t41, i64 0, 2
  %t43 = insertvalue %ax_arr undef, ptr @.bytes.47, 0
  %t44 = insertvalue %ax_arr %t43, i64 116, 1
  %t45 = insertvalue %ax_arr %t44, i64 0, 2
  %t46 = load %ax_arr, ptr %a33
  %t47 = insertvalue %ax_arr undef, ptr @.bytes.44, 0
  %t48 = insertvalue %ax_arr %t47, i64 6, 1
  %t49 = insertvalue %ax_arr %t48, i64 0, 2
  %t50 = load %ax_arr, ptr %a33
  %t51 = insertvalue %ax_arr undef, ptr @.bytes.48, 0
  %t52 = insertvalue %ax_arr %t51, i64 20, 1
  %t53 = insertvalue %ax_arr %t52, i64 0, 2
  %t54 = load %ax_arr, ptr %a33
  %t55 = insertvalue %ax_arr undef, ptr @.bytes.49, 0
  %t56 = insertvalue %ax_arr %t55, i64 20, 1
  %t57 = insertvalue %ax_arr %t56, i64 0, 2
  %t58 = load %ax_arr, ptr %a38
  %t59 = insertvalue %ax_arr undef, ptr @.bytes.50, 0
  %t60 = insertvalue %ax_arr %t59, i64 12, 1
  %t61 = insertvalue %ax_arr %t60, i64 0, 2
  %t62 = load %ax_arr, ptr %a38
  %t63 = insertvalue %ax_arr undef, ptr @.bytes.51, 0
  %t64 = insertvalue %ax_arr %t63, i64 4, 1
  %t65 = insertvalue %ax_arr %t64, i64 0, 2
  %t66 = load i1, ptr %a24
  br i1 %t66, label %then69, label %else70
then69:
  %t72 = insertvalue %ax_arr undef, ptr @.bytes.52, 0
  %t73 = insertvalue %ax_arr %t72, i64 53, 1
  %t74 = insertvalue %ax_arr %t73, i64 0, 2
  store %ax_arr %t74, ptr %a67
  store i64 0, ptr %a68
  br label %join71
else70:
  %t75 = insertvalue %ax_arr undef, ptr @.bytes.53, 0
  %t76 = insertvalue %ax_arr %t75, i64 0, 1
  %t77 = insertvalue %ax_arr %t76, i64 0, 2
  store %ax_arr %t77, ptr %a67
  store i64 0, ptr %a68
  br label %join71
join71:
  %t78 = load %ax_arr, ptr %a67
  %t79 = load i64, ptr %a68
  %t80 = insertvalue %ax_arr undef, ptr @.bytes.54, 0
  %t81 = insertvalue %ax_arr %t80, i64 3, 1
  %t82 = insertvalue %ax_arr %t81, i64 0, 2
  %t83 = load i64, ptr %a20
  %t84 = icmp eq i64 %t83, 1
  br i1 %t84, label %then87, label %else88
then87:
  %t90 = insertvalue %ax_arr undef, ptr @.bytes.55, 0
  %t91 = insertvalue %ax_arr %t90, i64 8, 1
  %t92 = insertvalue %ax_arr %t91, i64 0, 2
  store %ax_arr %t92, ptr %a85
  store i64 0, ptr %a86
  br label %join89
else88:
  %t93 = insertvalue %ax_arr undef, ptr @.bytes.56, 0
  %t94 = insertvalue %ax_arr %t93, i64 10, 1
  %t95 = insertvalue %ax_arr %t94, i64 0, 2
  store %ax_arr %t95, ptr %a85
  store i64 0, ptr %a86
  br label %join89
join89:
  %t96 = load %ax_arr, ptr %a85
  %t97 = load i64, ptr %a86
  %t98 = insertvalue %ax_arr undef, ptr @.bytes.57, 0
  %t99 = insertvalue %ax_arr %t98, i64 136, 1
  %t100 = insertvalue %ax_arr %t99, i64 0, 2
  %t101 = extractvalue %ax_arr %t46, 1
  %t102 = extractvalue %ax_arr %t50, 1
  %t103 = extractvalue %ax_arr %t54, 1
  %t104 = extractvalue %ax_arr %t58, 1
  %t105 = extractvalue %ax_arr %t62, 1
  %t106 = extractvalue %ax_arr %t78, 1
  %t107 = extractvalue %ax_arr %t96, 1
  %t108 = add i64 15, 116
  %t109 = add i64 %t108, %t101
  %t110 = add i64 %t109, 6
  %t111 = add i64 %t110, %t102
  %t112 = add i64 %t111, 20
  %t113 = add i64 %t112, %t103
  %t114 = add i64 %t113, 20
  %t115 = add i64 %t114, %t104
  %t116 = add i64 %t115, 12
  %t117 = add i64 %t116, %t105
  %t118 = add i64 %t117, 4
  %t119 = add i64 %t118, %t106
  %t120 = add i64 %t119, 3
  %t121 = add i64 %t120, %t107
  %t122 = add i64 %t121, 136
  br label %cat_fresh125
cat_fresh125:
  %t127 = icmp slt i64 %t122, 0
  %t128 = select i1 %t127, i64 0, i64 %t122
  %t129 = mul i64 %t128, 1
  %t130 = call ptr @ax_alloc(i64 %t129)
  %t131 = insertvalue %ax_arr undef, ptr %t130, 0
  %t132 = insertvalue %ax_arr %t131, i64 %t128, 1
  %t133 = insertvalue %ax_arr %t132, i64 1, 2
  %t134 = extractvalue %ax_arr %t133, 0
  %t135 = extractvalue %ax_arr %t42, 0
  %t136 = getelementptr inbounds i8, ptr %t134, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t136, ptr %t135, i64 15, i1 false)
  %t137 = add i64 0, 15
  %t138 = extractvalue %ax_arr %t45, 0
  %t139 = getelementptr inbounds i8, ptr %t134, i64 %t137
  call void @llvm.memcpy.p0.p0.i64(ptr %t139, ptr %t138, i64 116, i1 false)
  %t140 = add i64 %t137, 116
  %t141 = extractvalue %ax_arr %t46, 0
  %t142 = getelementptr inbounds i8, ptr %t134, i64 %t140
  call void @llvm.memcpy.p0.p0.i64(ptr %t142, ptr %t141, i64 %t101, i1 false)
  %t143 = add i64 %t140, %t101
  %t144 = extractvalue %ax_arr %t49, 0
  %t145 = getelementptr inbounds i8, ptr %t134, i64 %t143
  call void @llvm.memcpy.p0.p0.i64(ptr %t145, ptr %t144, i64 6, i1 false)
  %t146 = add i64 %t143, 6
  %t147 = extractvalue %ax_arr %t50, 0
  %t148 = getelementptr inbounds i8, ptr %t134, i64 %t146
  call void @llvm.memcpy.p0.p0.i64(ptr %t148, ptr %t147, i64 %t102, i1 false)
  %t149 = add i64 %t146, %t102
  %t150 = extractvalue %ax_arr %t53, 0
  %t151 = getelementptr inbounds i8, ptr %t134, i64 %t149
  call void @llvm.memcpy.p0.p0.i64(ptr %t151, ptr %t150, i64 20, i1 false)
  %t152 = add i64 %t149, 20
  %t153 = extractvalue %ax_arr %t54, 0
  %t154 = getelementptr inbounds i8, ptr %t134, i64 %t152
  call void @llvm.memcpy.p0.p0.i64(ptr %t154, ptr %t153, i64 %t103, i1 false)
  %t155 = add i64 %t152, %t103
  %t156 = extractvalue %ax_arr %t57, 0
  %t157 = getelementptr inbounds i8, ptr %t134, i64 %t155
  call void @llvm.memcpy.p0.p0.i64(ptr %t157, ptr %t156, i64 20, i1 false)
  %t158 = add i64 %t155, 20
  %t159 = extractvalue %ax_arr %t58, 0
  %t160 = getelementptr inbounds i8, ptr %t134, i64 %t158
  call void @llvm.memcpy.p0.p0.i64(ptr %t160, ptr %t159, i64 %t104, i1 false)
  %t161 = add i64 %t158, %t104
  %t162 = extractvalue %ax_arr %t61, 0
  %t163 = getelementptr inbounds i8, ptr %t134, i64 %t161
  call void @llvm.memcpy.p0.p0.i64(ptr %t163, ptr %t162, i64 12, i1 false)
  %t164 = add i64 %t161, 12
  %t165 = extractvalue %ax_arr %t62, 0
  %t166 = getelementptr inbounds i8, ptr %t134, i64 %t164
  call void @llvm.memcpy.p0.p0.i64(ptr %t166, ptr %t165, i64 %t105, i1 false)
  %t167 = add i64 %t164, %t105
  %t168 = extractvalue %ax_arr %t65, 0
  %t169 = getelementptr inbounds i8, ptr %t134, i64 %t167
  call void @llvm.memcpy.p0.p0.i64(ptr %t169, ptr %t168, i64 4, i1 false)
  %t170 = add i64 %t167, 4
  %t171 = extractvalue %ax_arr %t78, 0
  %t172 = getelementptr inbounds i8, ptr %t134, i64 %t170
  call void @llvm.memcpy.p0.p0.i64(ptr %t172, ptr %t171, i64 %t106, i1 false)
  %t173 = add i64 %t170, %t106
  %t174 = icmp ne i64 %t79, 0
  br i1 %t174, label %free175, label %cont176
free175:
  %t177 = extractvalue %ax_arr %t78, 0
  %t178 = extractvalue %ax_arr %t78, 1
  %t179 = mul i64 %t178, 1
  call void @ax_free(ptr %t177, i64 %t179)
  br label %cont176
cont176:
  %t180 = extractvalue %ax_arr %t82, 0
  %t181 = getelementptr inbounds i8, ptr %t134, i64 %t173
  call void @llvm.memcpy.p0.p0.i64(ptr %t181, ptr %t180, i64 3, i1 false)
  %t182 = add i64 %t173, 3
  %t183 = extractvalue %ax_arr %t96, 0
  %t184 = getelementptr inbounds i8, ptr %t134, i64 %t182
  call void @llvm.memcpy.p0.p0.i64(ptr %t184, ptr %t183, i64 %t107, i1 false)
  %t185 = add i64 %t182, %t107
  %t186 = icmp ne i64 %t97, 0
  br i1 %t186, label %free187, label %cont188
free187:
  %t189 = extractvalue %ax_arr %t96, 0
  %t190 = extractvalue %ax_arr %t96, 1
  %t191 = mul i64 %t190, 1
  call void @ax_free(ptr %t189, i64 %t191)
  br label %cont188
cont188:
  %t192 = extractvalue %ax_arr %t100, 0
  %t193 = getelementptr inbounds i8, ptr %t134, i64 %t185
  call void @llvm.memcpy.p0.p0.i64(ptr %t193, ptr %t192, i64 136, i1 false)
  %t194 = add i64 %t185, 136
  store %ax_arr %t133, ptr %a123
  br label %cat_join126
cat_join126:
  %t195 = load %ax_arr, ptr %a123
  %t196 = load i64, ptr %a39
  %t197 = icmp ne i64 %t196, 0
  %t198 = load %ax_arr, ptr %a38
  br i1 %t197, label %free199, label %cont200
free199:
  %t201 = extractvalue %ax_arr %t198, 0
  %t202 = extractvalue %ax_arr %t198, 1
  %t203 = mul i64 %t202, 1
  call void @ax_free(ptr %t201, i64 %t203)
  br label %cont200
cont200:
  %t204 = load i64, ptr %a34
  %t205 = icmp ne i64 %t204, 0
  %t206 = load %ax_arr, ptr %a33
  br i1 %t205, label %free207, label %cont208
free207:
  %t209 = extractvalue %ax_arr %t206, 0
  %t210 = extractvalue %ax_arr %t206, 1
  %t211 = mul i64 %t210, 1
  call void @ax_free(ptr %t209, i64 %t211)
  br label %cont208
cont208:
  %t212 = load i64, ptr %a18
  %t213 = icmp ne i64 %t212, 0
  %t214 = load %ax_arr, ptr %a17
  br i1 %t213, label %free215, label %cont216
free215:
  %t217 = extractvalue %ax_arr %t214, 0
  %t218 = extractvalue %ax_arr %t214, 1
  %t219 = mul i64 %t218, 1
  call void @ax_free(ptr %t217, i64 %t219)
  br label %cont216
cont216:
  %t220 = insertvalue %ax_arr %t195, i64 1, 2
  ret %ax_arr %t220
}

; page_response  graph:db366dad64dea69f
define internal %ax_arr @ax_page_response__par(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a11 = alloca %ax_arr
  %a12 = alloca i64
  %a28 = alloca %ax_arr
  store i64 %p_n, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call %ax_arr @ax_page__par(i64 %t2)
  %t4 = extractvalue %ax_arr %t3, 2
  store %ax_arr %t3, ptr %a5
  store i64 %t4, ptr %a6
  %t7 = load %ax_arr, ptr %a5
  %t8 = extractvalue %ax_arr %t7, 1
  %t9 = call %ax_arr @ax_utoa__par(i64 %t8)
  %t10 = extractvalue %ax_arr %t9, 2
  store %ax_arr %t9, ptr %a11
  store i64 %t10, ptr %a12
  %t13 = insertvalue %ax_arr undef, ptr @.bytes.61, 0
  %t14 = insertvalue %ax_arr %t13, i64 73, 1
  %t15 = insertvalue %ax_arr %t14, i64 0, 2
  %t16 = load %ax_arr, ptr %a11
  %t17 = load i64, ptr %a12
  store i64 0, ptr %a12
  %t18 = insertvalue %ax_arr undef, ptr @.bytes.23, 0
  %t19 = insertvalue %ax_arr %t18, i64 4, 1
  %t20 = insertvalue %ax_arr %t19, i64 0, 2
  %t21 = load %ax_arr, ptr %a5
  %t22 = load i64, ptr %a6
  store i64 0, ptr %a6
  %t23 = extractvalue %ax_arr %t16, 1
  %t24 = extractvalue %ax_arr %t21, 1
  %t25 = add i64 73, %t23
  %t26 = add i64 %t25, 4
  %t27 = add i64 %t26, %t24
  br label %cat_fresh30
cat_fresh30:
  %t32 = icmp slt i64 %t27, 0
  %t33 = select i1 %t32, i64 0, i64 %t27
  %t34 = mul i64 %t33, 1
  %t35 = call ptr @ax_alloc(i64 %t34)
  %t36 = insertvalue %ax_arr undef, ptr %t35, 0
  %t37 = insertvalue %ax_arr %t36, i64 %t33, 1
  %t38 = insertvalue %ax_arr %t37, i64 1, 2
  %t39 = extractvalue %ax_arr %t38, 0
  %t40 = extractvalue %ax_arr %t15, 0
  %t41 = getelementptr inbounds i8, ptr %t39, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t41, ptr %t40, i64 73, i1 false)
  %t42 = add i64 0, 73
  %t43 = extractvalue %ax_arr %t16, 0
  %t44 = getelementptr inbounds i8, ptr %t39, i64 %t42
  call void @llvm.memcpy.p0.p0.i64(ptr %t44, ptr %t43, i64 %t23, i1 false)
  %t45 = add i64 %t42, %t23
  %t46 = icmp ne i64 %t17, 0
  br i1 %t46, label %free47, label %cont48
free47:
  %t49 = extractvalue %ax_arr %t16, 0
  %t50 = extractvalue %ax_arr %t16, 1
  %t51 = mul i64 %t50, 1
  call void @ax_free(ptr %t49, i64 %t51)
  br label %cont48
cont48:
  %t52 = extractvalue %ax_arr %t20, 0
  %t53 = getelementptr inbounds i8, ptr %t39, i64 %t45
  call void @llvm.memcpy.p0.p0.i64(ptr %t53, ptr %t52, i64 4, i1 false)
  %t54 = add i64 %t45, 4
  %t55 = extractvalue %ax_arr %t21, 0
  %t56 = getelementptr inbounds i8, ptr %t39, i64 %t54
  call void @llvm.memcpy.p0.p0.i64(ptr %t56, ptr %t55, i64 %t24, i1 false)
  %t57 = add i64 %t54, %t24
  %t58 = icmp ne i64 %t22, 0
  br i1 %t58, label %free59, label %cont60
free59:
  %t61 = extractvalue %ax_arr %t21, 0
  %t62 = extractvalue %ax_arr %t21, 1
  %t63 = mul i64 %t62, 1
  call void @ax_free(ptr %t61, i64 %t63)
  br label %cont60
cont60:
  store %ax_arr %t38, ptr %a28
  br label %cat_join31
cat_join31:
  %t64 = load %ax_arr, ptr %a28
  %t65 = load i64, ptr %a12
  %t66 = icmp ne i64 %t65, 0
  %t67 = load %ax_arr, ptr %a11
  br i1 %t66, label %free68, label %cont69
free68:
  %t70 = extractvalue %ax_arr %t67, 0
  %t71 = extractvalue %ax_arr %t67, 1
  %t72 = mul i64 %t71, 1
  call void @ax_free(ptr %t70, i64 %t72)
  br label %cont69
cont69:
  %t73 = load i64, ptr %a6
  %t74 = icmp ne i64 %t73, 0
  %t75 = load %ax_arr, ptr %a5
  br i1 %t74, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t75, 0
  %t79 = extractvalue %ax_arr %t75, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = insertvalue %ax_arr %t64, i64 1, 2
  ret %ax_arr %t81
}

; page_response  graph:db366dad64dea69f
define internal %ax_arr @ax_page_response__seq(i64 %p_n) "no-builtins" {
entry:
  %a1 = alloca i64
  %a5 = alloca %ax_arr
  %a6 = alloca i64
  %a11 = alloca %ax_arr
  %a12 = alloca i64
  %a28 = alloca %ax_arr
  store i64 %p_n, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call %ax_arr @ax_page__seq(i64 %t2)
  %t4 = extractvalue %ax_arr %t3, 2
  store %ax_arr %t3, ptr %a5
  store i64 %t4, ptr %a6
  %t7 = load %ax_arr, ptr %a5
  %t8 = extractvalue %ax_arr %t7, 1
  %t9 = call %ax_arr @ax_utoa__seq(i64 %t8)
  %t10 = extractvalue %ax_arr %t9, 2
  store %ax_arr %t9, ptr %a11
  store i64 %t10, ptr %a12
  %t13 = insertvalue %ax_arr undef, ptr @.bytes.61, 0
  %t14 = insertvalue %ax_arr %t13, i64 73, 1
  %t15 = insertvalue %ax_arr %t14, i64 0, 2
  %t16 = load %ax_arr, ptr %a11
  %t17 = load i64, ptr %a12
  store i64 0, ptr %a12
  %t18 = insertvalue %ax_arr undef, ptr @.bytes.23, 0
  %t19 = insertvalue %ax_arr %t18, i64 4, 1
  %t20 = insertvalue %ax_arr %t19, i64 0, 2
  %t21 = load %ax_arr, ptr %a5
  %t22 = load i64, ptr %a6
  store i64 0, ptr %a6
  %t23 = extractvalue %ax_arr %t16, 1
  %t24 = extractvalue %ax_arr %t21, 1
  %t25 = add i64 73, %t23
  %t26 = add i64 %t25, 4
  %t27 = add i64 %t26, %t24
  br label %cat_fresh30
cat_fresh30:
  %t32 = icmp slt i64 %t27, 0
  %t33 = select i1 %t32, i64 0, i64 %t27
  %t34 = mul i64 %t33, 1
  %t35 = call ptr @ax_alloc(i64 %t34)
  %t36 = insertvalue %ax_arr undef, ptr %t35, 0
  %t37 = insertvalue %ax_arr %t36, i64 %t33, 1
  %t38 = insertvalue %ax_arr %t37, i64 1, 2
  %t39 = extractvalue %ax_arr %t38, 0
  %t40 = extractvalue %ax_arr %t15, 0
  %t41 = getelementptr inbounds i8, ptr %t39, i64 0
  call void @llvm.memcpy.p0.p0.i64(ptr %t41, ptr %t40, i64 73, i1 false)
  %t42 = add i64 0, 73
  %t43 = extractvalue %ax_arr %t16, 0
  %t44 = getelementptr inbounds i8, ptr %t39, i64 %t42
  call void @llvm.memcpy.p0.p0.i64(ptr %t44, ptr %t43, i64 %t23, i1 false)
  %t45 = add i64 %t42, %t23
  %t46 = icmp ne i64 %t17, 0
  br i1 %t46, label %free47, label %cont48
free47:
  %t49 = extractvalue %ax_arr %t16, 0
  %t50 = extractvalue %ax_arr %t16, 1
  %t51 = mul i64 %t50, 1
  call void @ax_free(ptr %t49, i64 %t51)
  br label %cont48
cont48:
  %t52 = extractvalue %ax_arr %t20, 0
  %t53 = getelementptr inbounds i8, ptr %t39, i64 %t45
  call void @llvm.memcpy.p0.p0.i64(ptr %t53, ptr %t52, i64 4, i1 false)
  %t54 = add i64 %t45, 4
  %t55 = extractvalue %ax_arr %t21, 0
  %t56 = getelementptr inbounds i8, ptr %t39, i64 %t54
  call void @llvm.memcpy.p0.p0.i64(ptr %t56, ptr %t55, i64 %t24, i1 false)
  %t57 = add i64 %t54, %t24
  %t58 = icmp ne i64 %t22, 0
  br i1 %t58, label %free59, label %cont60
free59:
  %t61 = extractvalue %ax_arr %t21, 0
  %t62 = extractvalue %ax_arr %t21, 1
  %t63 = mul i64 %t62, 1
  call void @ax_free(ptr %t61, i64 %t63)
  br label %cont60
cont60:
  store %ax_arr %t38, ptr %a28
  br label %cat_join31
cat_join31:
  %t64 = load %ax_arr, ptr %a28
  %t65 = load i64, ptr %a12
  %t66 = icmp ne i64 %t65, 0
  %t67 = load %ax_arr, ptr %a11
  br i1 %t66, label %free68, label %cont69
free68:
  %t70 = extractvalue %ax_arr %t67, 0
  %t71 = extractvalue %ax_arr %t67, 1
  %t72 = mul i64 %t71, 1
  call void @ax_free(ptr %t70, i64 %t72)
  br label %cont69
cont69:
  %t73 = load i64, ptr %a6
  %t74 = icmp ne i64 %t73, 0
  %t75 = load %ax_arr, ptr %a5
  br i1 %t74, label %free76, label %cont77
free76:
  %t78 = extractvalue %ax_arr %t75, 0
  %t79 = extractvalue %ax_arr %t75, 1
  %t80 = mul i64 %t79, 1
  call void @ax_free(ptr %t78, i64 %t80)
  br label %cont77
cont77:
  %t81 = insertvalue %ax_arr %t64, i64 1, 2
  ret %ax_arr %t81
}

; handle  graph:fb731cbfadcff1b0
define internal %ax_arr @ax_handle__par(%ax_arr %p_req) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a14 = alloca i1
  %a25 = alloca i1
  %a27 = alloca i1
  %a38 = alloca %ax_arr
  %a39 = alloca i64
  %a44 = alloca i64
  %a52 = alloca i64
  %a55 = alloca i1
  %a61 = alloca %ax_arr
  %a62 = alloca i64
  %a81 = alloca %ax_arr
  %a82 = alloca i64
  store %ax_arr %p_req, ptr %a1
  %t3 = extractvalue %ax_arr %p_req, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load %ax_arr, ptr %a1
  %t8 = insertvalue %ax_arr %t7, i64 0, 2
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.62, 0
  %t10 = insertvalue %ax_arr %t9, i64 6, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = call i1 @ax_starts_with__par(%ax_arr %t8, %ax_arr %t12)
  store i1 %t13, ptr %a14
  br i1 %t13, label %join16, label %rhs15
rhs15:
  %t17 = load %ax_arr, ptr %a1
  %t18 = insertvalue %ax_arr %t17, i64 0, 2
  %t19 = insertvalue %ax_arr undef, ptr @.bytes.63, 0
  %t20 = insertvalue %ax_arr %t19, i64 6, 1
  %t21 = insertvalue %ax_arr %t20, i64 0, 2
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = call i1 @ax_starts_with__par(%ax_arr %t18, %ax_arr %t22)
  store i1 %t23, ptr %a14
  br label %join16
join16:
  %t24 = load i1, ptr %a14
  store i1 %t24, ptr %a25
  %t26 = load i1, ptr %a25
  store i1 %t26, ptr %a27
  br i1 %t26, label %join29, label %rhs28
rhs28:
  %t30 = load %ax_arr, ptr %a1
  %t31 = insertvalue %ax_arr %t30, i64 0, 2
  %t32 = insertvalue %ax_arr undef, ptr @.bytes.64, 0
  %t33 = insertvalue %ax_arr %t32, i64 10, 1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = call i1 @ax_starts_with__par(%ax_arr %t31, %ax_arr %t35)
  store i1 %t36, ptr %a27
  br label %join29
join29:
  %t37 = load i1, ptr %a27
  br i1 %t37, label %then40, label %else41
then40:
  %t43 = load i1, ptr %a25
  br i1 %t43, label %then45, label %else46
then45:
  store i64 3, ptr %a44
  br label %join47
else46:
  %t48 = load %ax_arr, ptr %a1
  %t49 = insertvalue %ax_arr %t48, i64 0, 2
  %t50 = call i64 @ax_page_count__par(%ax_arr %t49)
  store i64 %t50, ptr %a44
  br label %join47
join47:
  %t51 = load i64, ptr %a44
  store i64 %t51, ptr %a52
  %t53 = load i64, ptr %a52
  %t54 = icmp slt i64 %t53, 1
  store i1 %t54, ptr %a55
  br i1 %t54, label %join57, label %rhs56
rhs56:
  %t58 = load i64, ptr %a52
  %t59 = icmp sgt i64 %t58, 1000
  store i1 %t59, ptr %a55
  br label %join57
join57:
  %t60 = load i1, ptr %a55
  br i1 %t60, label %then63, label %else64
then63:
  %t66 = insertvalue %ax_arr undef, ptr @.bytes.65, 0
  %t67 = insertvalue %ax_arr %t66, i64 104, 1
  %t68 = insertvalue %ax_arr %t67, i64 0, 2
  store %ax_arr %t68, ptr %a61
  store i64 0, ptr %a62
  br label %join65
else64:
  %t69 = load i64, ptr %a52
  %t70 = call %ax_arr @ax_page_response__par(i64 %t69)
  %t71 = extractvalue %ax_arr %t70, 2
  store %ax_arr %t70, ptr %a61
  store i64 %t71, ptr %a62
  br label %join65
join65:
  %t72 = load %ax_arr, ptr %a61
  %t73 = load i64, ptr %a62
  store %ax_arr %t72, ptr %a38
  store i64 %t73, ptr %a39
  br label %join42
else41:
  %t74 = load %ax_arr, ptr %a1
  %t75 = insertvalue %ax_arr %t74, i64 0, 2
  %t76 = insertvalue %ax_arr undef, ptr @.bytes.66, 0
  %t77 = insertvalue %ax_arr %t76, i64 4, 1
  %t78 = insertvalue %ax_arr %t77, i64 0, 2
  %t79 = insertvalue %ax_arr %t78, i64 0, 2
  %t80 = call i1 @ax_starts_with__par(%ax_arr %t75, %ax_arr %t79)
  br i1 %t80, label %then83, label %else84
then83:
  %t86 = insertvalue %ax_arr undef, ptr @.bytes.67, 0
  %t87 = insertvalue %ax_arr %t86, i64 80, 1
  %t88 = insertvalue %ax_arr %t87, i64 0, 2
  store %ax_arr %t88, ptr %a81
  store i64 0, ptr %a82
  br label %join85
else84:
  %t89 = insertvalue %ax_arr undef, ptr @.bytes.68, 0
  %t90 = insertvalue %ax_arr %t89, i64 54, 1
  %t91 = insertvalue %ax_arr %t90, i64 0, 2
  store %ax_arr %t91, ptr %a81
  store i64 0, ptr %a82
  br label %join85
join85:
  %t92 = load %ax_arr, ptr %a81
  %t93 = load i64, ptr %a82
  store %ax_arr %t92, ptr %a38
  store i64 %t93, ptr %a39
  br label %join42
join42:
  %t94 = load %ax_arr, ptr %a38
  %t95 = load i64, ptr %a39
  %t96 = icmp ne i64 %t95, 0
  %t97 = load i64, ptr %a2
  %t98 = icmp ne i64 %t97, 0
  %t99 = load %ax_arr, ptr %a1
  %t100 = and i1 %t98, %t96
  br i1 %t100, label %free101, label %cont102
free101:
  %t103 = extractvalue %ax_arr %t99, 0
  %t104 = extractvalue %ax_arr %t99, 1
  %t105 = mul i64 %t104, 1
  call void @ax_free(ptr %t103, i64 %t105)
  br label %cont102
cont102:
  %t106 = insertvalue %ax_arr %t94, i64 %t95, 2
  ret %ax_arr %t106
}

; handle  graph:fb731cbfadcff1b0
define internal %ax_arr @ax_handle__seq(%ax_arr %p_req) "no-builtins" {
entry:
  %a1 = alloca %ax_arr
  %a2 = alloca i64
  %a6 = alloca i64
  %a14 = alloca i1
  %a25 = alloca i1
  %a27 = alloca i1
  %a38 = alloca %ax_arr
  %a39 = alloca i64
  %a44 = alloca i64
  %a52 = alloca i64
  %a55 = alloca i1
  %a61 = alloca %ax_arr
  %a62 = alloca i64
  %a81 = alloca %ax_arr
  %a82 = alloca i64
  store %ax_arr %p_req, ptr %a1
  %t3 = extractvalue %ax_arr %p_req, 2
  store i64 %t3, ptr %a2
  %t4 = load %ax_arr, ptr %a1
  %t5 = extractvalue %ax_arr %t4, 1
  store i64 %t5, ptr %a6
  %t7 = load %ax_arr, ptr %a1
  %t8 = insertvalue %ax_arr %t7, i64 0, 2
  %t9 = insertvalue %ax_arr undef, ptr @.bytes.62, 0
  %t10 = insertvalue %ax_arr %t9, i64 6, 1
  %t11 = insertvalue %ax_arr %t10, i64 0, 2
  %t12 = insertvalue %ax_arr %t11, i64 0, 2
  %t13 = call i1 @ax_starts_with__seq(%ax_arr %t8, %ax_arr %t12)
  store i1 %t13, ptr %a14
  br i1 %t13, label %join16, label %rhs15
rhs15:
  %t17 = load %ax_arr, ptr %a1
  %t18 = insertvalue %ax_arr %t17, i64 0, 2
  %t19 = insertvalue %ax_arr undef, ptr @.bytes.63, 0
  %t20 = insertvalue %ax_arr %t19, i64 6, 1
  %t21 = insertvalue %ax_arr %t20, i64 0, 2
  %t22 = insertvalue %ax_arr %t21, i64 0, 2
  %t23 = call i1 @ax_starts_with__seq(%ax_arr %t18, %ax_arr %t22)
  store i1 %t23, ptr %a14
  br label %join16
join16:
  %t24 = load i1, ptr %a14
  store i1 %t24, ptr %a25
  %t26 = load i1, ptr %a25
  store i1 %t26, ptr %a27
  br i1 %t26, label %join29, label %rhs28
rhs28:
  %t30 = load %ax_arr, ptr %a1
  %t31 = insertvalue %ax_arr %t30, i64 0, 2
  %t32 = insertvalue %ax_arr undef, ptr @.bytes.64, 0
  %t33 = insertvalue %ax_arr %t32, i64 10, 1
  %t34 = insertvalue %ax_arr %t33, i64 0, 2
  %t35 = insertvalue %ax_arr %t34, i64 0, 2
  %t36 = call i1 @ax_starts_with__seq(%ax_arr %t31, %ax_arr %t35)
  store i1 %t36, ptr %a27
  br label %join29
join29:
  %t37 = load i1, ptr %a27
  br i1 %t37, label %then40, label %else41
then40:
  %t43 = load i1, ptr %a25
  br i1 %t43, label %then45, label %else46
then45:
  store i64 3, ptr %a44
  br label %join47
else46:
  %t48 = load %ax_arr, ptr %a1
  %t49 = insertvalue %ax_arr %t48, i64 0, 2
  %t50 = call i64 @ax_page_count__seq(%ax_arr %t49)
  store i64 %t50, ptr %a44
  br label %join47
join47:
  %t51 = load i64, ptr %a44
  store i64 %t51, ptr %a52
  %t53 = load i64, ptr %a52
  %t54 = icmp slt i64 %t53, 1
  store i1 %t54, ptr %a55
  br i1 %t54, label %join57, label %rhs56
rhs56:
  %t58 = load i64, ptr %a52
  %t59 = icmp sgt i64 %t58, 1000
  store i1 %t59, ptr %a55
  br label %join57
join57:
  %t60 = load i1, ptr %a55
  br i1 %t60, label %then63, label %else64
then63:
  %t66 = insertvalue %ax_arr undef, ptr @.bytes.65, 0
  %t67 = insertvalue %ax_arr %t66, i64 104, 1
  %t68 = insertvalue %ax_arr %t67, i64 0, 2
  store %ax_arr %t68, ptr %a61
  store i64 0, ptr %a62
  br label %join65
else64:
  %t69 = load i64, ptr %a52
  %t70 = call %ax_arr @ax_page_response__seq(i64 %t69)
  %t71 = extractvalue %ax_arr %t70, 2
  store %ax_arr %t70, ptr %a61
  store i64 %t71, ptr %a62
  br label %join65
join65:
  %t72 = load %ax_arr, ptr %a61
  %t73 = load i64, ptr %a62
  store %ax_arr %t72, ptr %a38
  store i64 %t73, ptr %a39
  br label %join42
else41:
  %t74 = load %ax_arr, ptr %a1
  %t75 = insertvalue %ax_arr %t74, i64 0, 2
  %t76 = insertvalue %ax_arr undef, ptr @.bytes.66, 0
  %t77 = insertvalue %ax_arr %t76, i64 4, 1
  %t78 = insertvalue %ax_arr %t77, i64 0, 2
  %t79 = insertvalue %ax_arr %t78, i64 0, 2
  %t80 = call i1 @ax_starts_with__seq(%ax_arr %t75, %ax_arr %t79)
  br i1 %t80, label %then83, label %else84
then83:
  %t86 = insertvalue %ax_arr undef, ptr @.bytes.67, 0
  %t87 = insertvalue %ax_arr %t86, i64 80, 1
  %t88 = insertvalue %ax_arr %t87, i64 0, 2
  store %ax_arr %t88, ptr %a81
  store i64 0, ptr %a82
  br label %join85
else84:
  %t89 = insertvalue %ax_arr undef, ptr @.bytes.68, 0
  %t90 = insertvalue %ax_arr %t89, i64 54, 1
  %t91 = insertvalue %ax_arr %t90, i64 0, 2
  store %ax_arr %t91, ptr %a81
  store i64 0, ptr %a82
  br label %join85
join85:
  %t92 = load %ax_arr, ptr %a81
  %t93 = load i64, ptr %a82
  store %ax_arr %t92, ptr %a38
  store i64 %t93, ptr %a39
  br label %join42
join42:
  %t94 = load %ax_arr, ptr %a38
  %t95 = load i64, ptr %a39
  %t96 = icmp ne i64 %t95, 0
  %t97 = load i64, ptr %a2
  %t98 = icmp ne i64 %t97, 0
  %t99 = load %ax_arr, ptr %a1
  %t100 = and i1 %t98, %t96
  br i1 %t100, label %free101, label %cont102
free101:
  %t103 = extractvalue %ax_arr %t99, 0
  %t104 = extractvalue %ax_arr %t99, 1
  %t105 = mul i64 %t104, 1
  call void @ax_free(ptr %t103, i64 %t105)
  br label %cont102
cont102:
  %t106 = insertvalue %ax_arr %t94, i64 %t95, 2
  ret %ax_arr %t106
}

; main  graph:526b428deaceb962
define internal i64 @ax_main__seq(i64 %p_port) "no-builtins" {
entry:
  %a1 = alloca i64
  store i64 %p_port, ptr %a1
  %t2 = load i64, ptr %a1
  %t3 = call i64 @ax_serve(i64 %t2, ptr @ax_handle__seq)
  ret i64 %t3
}

define i32 @main(i32 %argc, ptr %argv) {
entry:
  %a11 = alloca i64
  %t1 = zext i32 %argc to i64
  %t2 = getelementptr ptr, ptr %argv, i64 %t1
  %t3 = getelementptr ptr, ptr %t2, i64 1
  call void @ax_runtime_init(ptr %t3)
  %t4 = icmp eq i32 %argc, 2
  br i1 %t4, label %parse5, label %usage6
usage6:
  %t7 = load ptr, ptr %argv
  call void @ax_usage(ptr %t7, ptr @.str.4)
  ret i32 2
parse5:
  %t8 = getelementptr inbounds ptr, ptr %argv, i64 1
  %t9 = load ptr, ptr %t8
  %t10 = call i64 @ax_parse_i64(ptr %t9, ptr @.str.4)
  store i64 %t10, ptr %a11
  %t12 = load i64, ptr %a11
  %t13 = icmp sgt i64 %t12, 0
  br i1 %t13, label %pre_ok14, label %pre_fail15
pre_fail15:
  call void @ax_precondition_failed(ptr @.str.5)
  ret i32 3
pre_ok14:
  %t16 = load i64, ptr %a11
  %t17 = icmp slt i64 %t16, 65536
  br i1 %t17, label %pre_ok18, label %pre_fail19
pre_fail19:
  call void @ax_precondition_failed(ptr @.str.6)
  ret i32 3
pre_ok18:
  %t20 = load i64, ptr %a11
  %t21 = call i64 @ax_main__seq(i64 %t20)
  call void @ax_print_i64(i64 %t21)
  ret i32 0
}

define void @_start() naked noreturn {
  call void asm sideeffect "mov x0, sp\0Abl ax_process_start\0Abrk #0", "~{memory}"()
  unreachable
}

define void @ax_process_start(ptr %stack) noreturn {
  %argc64 = load i64, ptr %stack
  %argc = trunc i64 %argc64 to i32
  %argv = getelementptr i64, ptr %stack, i64 1
  %status = call i32 @main(i32 %argc, ptr %argv)
  %status64 = sext i32 %status to i64
  call void @ax_exit(i64 %status64)
  unreachable
}
