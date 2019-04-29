resource "aws_sqs_queue" "internal" {
  provider = "aws.internal"
  name     = "jinjaform-tests-aws-internal"
}

resource "aws_sqs_queue" "playground" {
  name = "jinjaform-tests-aws-playground"
}
