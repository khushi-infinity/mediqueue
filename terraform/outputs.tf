output "vpc_id" {
  value = module.vpc.vpc_id
}
output "public_subnets" {
  value = module.vpc.public_subnets
}
output "private_subnets" {
  value = module.vpc.private_subnets
}
output "cluster_name" {
  value = module.eks.cluster_name
}
output "configure_kubectl" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
