'use client';

import { useState } from 'react';
import {
  Box,
  Button,
  Input,
  Text,
  VStack,
  HStack,
  Heading,
  Divider,
  Card,
  CardBody,
  CardHeader,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { sendQuery, QueryResult } from '@/services/api';

export default function SearchComponent() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await sendQuery(query);
      setResult(data);
    } catch (err) {
      setError(`Failed to fetch results: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box p={5} maxW="1000px" mx="auto">
      <VStack spacing={6} align="stretch">
        <Heading as="h1" size="xl" textAlign="center" mb={4}>
          Westeros Laws Query System
        </Heading>
        <Text textAlign="center" fontSize="lg" mb={6}>
          Ask questions about the laws of the Seven Kingdoms
        </Text>

        <HStack>
          <Input
            placeholder="e.g., What happens if I steal from the Sept?"
            value={query}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            size="lg"
            borderRadius="md"
          />
          <Button
            colorScheme="blue"
            onClick={handleSearch}
            isLoading={isLoading}
            loadingText="Searching"
            size="lg"
          >
            Search
          </Button>
        </HStack>

        {error && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <AlertTitle mr={2}>Error!</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading && (
          <Box textAlign="center" py={10}>
            <Spinner size="xl" />
            <Text mt={4}>Consulting the maesters...</Text>
          </Box>
        )}

        {result && !isLoading && (
          <VStack spacing={6} align="stretch" mt={4}>
            <Card variant="outline">
              <CardHeader>
                <Heading size="md">Response</Heading>
              </CardHeader>
              <CardBody>
                <Text whiteSpace="pre-wrap">{result.response}</Text>
              </CardBody>
            </Card>

            {result.citations.length > 0 && (
              <Card variant="outline">
                <CardHeader>
                  <Heading size="md">Citations</Heading>
                </CardHeader>
                <CardBody>
                  <VStack spacing={4} align="stretch">
                    {result.citations.map((citation, index) => (
                      <Box key={index} p={4} borderWidth="1px" borderRadius="md">
                        <Text fontWeight="bold" mb={2}>
                          Source: {citation.source}
                        </Text>
                        <Text>{citation.text}</Text>
                      </Box>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            )}
          </VStack>
        )}
      </VStack>
    </Box>
  );
}